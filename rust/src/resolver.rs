use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::PyTuple;

use crate::error::PranceError;
use crate::fetch::{DocumentCache, fetch_url};
use crate::path::{Path, obj_path_to_rust, path_get, path_set};
use crate::url::{ParsedUrl, split_fragment_reference, split_url_reference, urlresource};
use crate::value::{Key, Value};
use crate::{RESOLVE_ALL, RESOLVE_FILES, RESOLVE_HTTP, RESOLVE_INTERNAL, TRANSLATE_DEFAULT, TRANSLATE_EXTERNAL};

type RefPath = (String, Vec<String>);
type RecursionStack = Vec<RefPath>;

pub struct ResolveOptions {
    pub copy_input: bool,
    pub recursion_limit: u32,
    pub resolve_types: u32,
    pub resolve_method: u32,
    pub encoding: Option<String>,
    pub strict: bool,
    pub fragment_copy: bool,
    pub recursion_limit_handler: Option<Py<PyAny>>,
}

impl ResolveOptions {
    pub fn clone_for_thread(&self, py: Python<'_>) -> Self {
        Self {
            copy_input: self.copy_input,
            recursion_limit: self.recursion_limit,
            resolve_types: self.resolve_types,
            resolve_method: self.resolve_method,
            encoding: self.encoding.clone(),
            strict: self.strict,
            fragment_copy: self.fragment_copy,
            recursion_limit_handler: self
                .recursion_limit_handler
                .as_ref()
                .map(|h| h.clone_ref(py)),
        }
    }
}

impl Default for ResolveOptions {
    fn default() -> Self {
        Self {
            copy_input: true,
            recursion_limit: 1,
            recursion_limit_handler: None,
            resolve_types: RESOLVE_ALL,
            resolve_method: TRANSLATE_DEFAULT,
            encoding: None,
            strict: true,
            fragment_copy: true,
        }
    }
}

pub struct ResolverContext {
    pub opts: ResolveOptions,
    pub root_url: Option<ParsedUrl>,
    pub cache: DocumentCache,
    pub fragment_cache: HashMap<(RefPath, u32), Value>,
    pub soft_dereference_objs: HashMap<String, Value>,
}

impl ResolverContext {
    pub fn new(opts: ResolveOptions, root_url: Option<ParsedUrl>, cache: DocumentCache) -> Self {
        Self {
            opts,
            root_url,
            cache,
            fragment_cache: HashMap::new(),
            soft_dereference_objs: HashMap::new(),
        }
    }

    pub fn seed_root(&mut self, specs: &Value) {
        if let Some(ref url) = self.root_url {
            let key = crate::fetch::CacheKey {
                resource: urlresource(url),
                strict: self.opts.strict,
            };
            if self.cache.get_document(&key).is_none() {
                self.cache.insert_document(key, specs.deep_copy());
            }
        }
    }
}

pub fn resolve_value(
    specs: Value,
    base_url: Option<ParsedUrl>,
    opts: ResolveOptions,
    cache: DocumentCache,
) -> Result<Value, PranceError> {
    let mut ctx = ResolverContext::new(opts, base_url.clone(), cache);
    ctx.seed_root(&specs);
    ctx.fragment_cache.clear();
    let mut specs = resolve_partial(&mut ctx, base_url.as_ref(), specs, vec![], HashMap::new())?;

    if !ctx.soft_dereference_objs.is_empty() {
        ensure_components_schemas(&mut specs);
        merge_soft_refs(&mut specs, ctx.soft_dereference_objs);
    }

    Ok(specs)
}

fn merge_soft_refs(specs: &mut Value, soft: HashMap<String, Value>) {
    if let Value::Object(entries) = specs {
        for (k, v) in entries.iter_mut() {
            if k.as_str() == Some("components") {
                if let Value::Object(comp_entries) = v {
                    for (ck, cv) in comp_entries.iter_mut() {
                        if ck.as_str() == Some("schemas") {
                            if let Value::Object(schema_entries) = cv {
                                for (sk, sv) in &soft {
                                    schema_entries.push((Key::Str(sk.clone()), sv.clone()));
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

fn ensure_components_schemas(specs: &mut Value) {
    if let Value::Object(entries) = specs {
        let mut has_components = false;
        let mut has_schemas = false;
        for (k, v) in entries.iter() {
            if k.as_str() == Some("components") {
                has_components = true;
                if let Value::Object(ce) = v {
                    for (ck, _) in ce.iter() {
                        if ck.as_str() == Some("schemas") {
                            has_schemas = true;
                        }
                    }
                }
            }
        }
        if !has_components {
            entries.push((
                Key::Str("components".into()),
                Value::Object(vec![(
                    Key::Str("schemas".into()),
                    Value::Object(Vec::new()),
                )]),
            ));
        } else if !has_schemas {
            for (k, v) in entries.iter_mut() {
                if k.as_str() == Some("components") {
                    if let Value::Object(ce) = v {
                        ce.push((Key::Str("schemas".into()), Value::Object(Vec::new())));
                    }
                }
            }
        }
    }
}

fn resolve_partial(
    ctx: &mut ResolverContext,
    base_url: Option<&ParsedUrl>,
    partial: Value,
    recursions: RecursionStack,
    recursion_counts: HashMap<RefPath, u32>,
) -> Result<Value, PranceError> {
    let changes = dereferencing_iterator(
        ctx,
        base_url,
        &partial,
        vec![],
        &recursions,
        &recursion_counts,
    )?;

    let mut paths: Vec<Path> = changes.keys().cloned().collect();
    paths.sort_by_key(|p| p.len());

    let mut partial = partial;
    for path in paths {
        if let Some(value) = changes.get(&path) {
            if path.is_empty() {
                partial = value.clone();
            } else {
                path_set(&mut partial, &path, value.clone())?;
            }
        }
    }
    Ok(partial)
}

fn dereferencing_iterator(
    ctx: &mut ResolverContext,
    base_url: Option<&ParsedUrl>,
    partial: &Value,
    parent_path: Path,
    recursions: &RecursionStack,
    recursion_counts: &HashMap<RefPath, u32>,
) -> Result<HashMap<Path, Value>, PranceError> {
    let mut changes = HashMap::new();

    for (item_path, refstring) in reference_iterator(partial, &Vec::new())? {
        let (ref_url, obj_path) = split_reference(base_url, &refstring)?;

        let translate = ctx.opts.resolve_method == TRANSLATE_EXTERNAL
            && ctx
                .root_url
                .as_ref()
                .map(|u| u.path.as_str())
                != Some(ref_url.path.as_str());

        if skip_reference(base_url, &ref_url, ctx.opts.resolve_types)? {
            continue;
        }

        let ref_path: RefPath = (urlresource(&ref_url), obj_path.clone());
        let depth = recursion_counts.get(&ref_path).copied().unwrap_or(0);
        let mut next_recursions = recursions.clone();
        next_recursions.push(ref_path.clone());
        let mut next_counts = recursion_counts.clone();
        next_counts.insert(ref_path.clone(), depth + 1);

        let ref_value = if depth >= ctx.opts.recursion_limit {
            call_reclimit_handler(ctx, &ref_url, &next_recursions)?
        } else {
            dereference(
                ctx,
                &ref_url,
                &obj_path,
                &next_recursions,
                &ref_path,
                depth,
                &next_counts,
            )?
        };

        let mut full_path = parent_path.clone();
        full_path.extend(item_path);

        if translate {
            let schema_url = collect_soft_refs(ctx, &ref_url, &obj_path, ref_value);
            changes.insert(
                full_path,
                Value::Object(vec![(
                    Key::Str("$ref".into()),
                    Value::Str(format!("#/components/schemas/{schema_url}")),
                )]),
            );
        } else {
            changes.insert(full_path, ref_value);
        }
    }

    Ok(changes)
}

fn split_reference(
    base_url: Option<&ParsedUrl>,
    refstring: &str,
) -> Result<(ParsedUrl, Vec<String>), PranceError> {
    if let Some(result) = split_fragment_reference(base_url, refstring) {
        return Ok(result);
    }
    split_url_reference(base_url, refstring)
}

fn collect_soft_refs(
    ctx: &mut ResolverContext,
    ref_url: &ParsedUrl,
    item_path: &[String],
    value: Value,
) -> String {
    let path_parts: Vec<&str> = ref_url.path.split('/').collect();
    let last = path_parts.last().copied().unwrap_or("");
    let suffix = if item_path.len() > 1 {
        item_path[1..].join("_")
    } else {
        String::new()
    };
    let dref_url = if suffix.is_empty() {
        last.to_string()
    } else {
        format!("{last}_{suffix}")
    };
    ctx.soft_dereference_objs.insert(dref_url.clone(), value);
    dref_url
}

fn skip_reference(
    base_url: Option<&ParsedUrl>,
    ref_url: &ParsedUrl,
    resolve_types: u32,
) -> Result<bool, PranceError> {
    if ref_url.scheme.starts_with("http") {
        return Ok((resolve_types & RESOLVE_HTTP) == 0);
    }
    if ref_url.scheme == "file" || ref_url.scheme == "python" || ref_url.scheme.is_empty() {
        let same_path = base_url.map(|b| b.path.as_str()) == Some(ref_url.path.as_str());
        if same_path {
            return Ok((resolve_types & RESOLVE_INTERNAL) == 0);
        }
        return Ok((resolve_types & RESOLVE_FILES) == 0);
    }
    Err(PranceError::Value(format!(
        "Scheme {:?} is not recognized in reference URL: {}",
        ref_url.scheme,
        ref_url.geturl()
    )))
}

fn fetch_cached_contents(ctx: &mut ResolverContext, ref_url: &ParsedUrl) -> Result<Value, PranceError> {
    let key = crate::fetch::CacheKey {
        resource: urlresource(ref_url),
        strict: ctx.opts.strict,
    };
    if let Some(entry) = ctx.cache.get_document(&key) {
        return Ok(entry);
    }
    Python::with_gil(|py| {
        fetch_url(
            py,
            ref_url,
            &ctx.cache,
            ctx.opts.encoding.as_deref(),
            ctx.opts.strict,
        )
    })
}

fn dereference(
    ctx: &mut ResolverContext,
    ref_url: &ParsedUrl,
    obj_path: &[String],
    recursions: &RecursionStack,
    ref_path: &RefPath,
    depth: u32,
    recursion_counts: &HashMap<RefPath, u32>,
) -> Result<Value, PranceError> {
    let cache_key = (ref_path.clone(), depth);
    if let Some(cached) = ctx.fragment_cache.get(&cache_key) {
        if !ctx.opts.fragment_copy && !ctx.opts.copy_input {
            return Ok(cached.clone());
        }
        return Ok(cached.deep_copy());
    }

    let contents = fetch_cached_contents(ctx, ref_url)?;
    let mut value = if obj_path.is_empty() {
        contents.clone()
    } else {
        let path = obj_path_to_rust(obj_path);
        path_get(&contents, &path).map_err(|e| {
            PranceError::Resolution(format!(
                "Cannot resolve reference \"{}\": {e}",
                ref_url.geturl()
            ))
        })?
    };

    value = value.deep_copy();
    value = resolve_partial(
        ctx,
        Some(ref_url),
        value,
        recursions.clone(),
        recursion_counts.clone(),
    )?;

    ctx.fragment_cache.insert(cache_key, value.clone());
    Ok(value)
}

fn call_reclimit_handler(
    ctx: &ResolverContext,
    ref_url: &ParsedUrl,
    recursions: &RecursionStack,
) -> Result<Value, PranceError> {
    Python::with_gil(|py| {
        let handler: Py<PyAny> = if let Some(ref h) = ctx.opts.recursion_limit_handler {
            h.clone_ref(py)
        } else {
            let resolver_mod = py.import("prance.util.resolver")?;
            resolver_mod.getattr("default_reclimit_handler")?.unbind()
        };

        let py_url = ref_url.to_py_parse_result(py)?;
        let mut py_recs = Vec::new();
        for (resource, obj_path) in recursions {
            let path_tuple = PyTuple::new(py, obj_path.iter().map(String::as_str))?;
            let resource_obj = resource.to_string().into_pyobject(py).unwrap();
            let tuple = PyTuple::new(
                py,
                [resource_obj.into_any(), path_tuple.into_any()],
            )?;
            py_recs.push(tuple);
        }
        let recs_tuple = PyTuple::new(py, py_recs)?;

        let result = handler.call1(py, (ctx.opts.recursion_limit, py_url, recs_tuple))?;
        let bound = result.bind(py);
        crate::convert::py_to_value(&bound, &mut crate::convert::OpaquePool::new())
            .map_err(|e| PranceError::Resolution(e.to_string()))
    })
}

fn reference_iterator(value: &Value, path: &Path) -> Result<Vec<(Path, String)>, PranceError> {
    let mut results = Vec::new();
    reference_iterator_impl(value, path, &mut results)?;
    Ok(results)
}

fn reference_iterator_impl(
    value: &Value,
    path: &Path,
    out: &mut Vec<(Path, String)>,
) -> Result<(), PranceError> {
    match value {
        Value::Object(entries) => {
            for (k, v) in entries {
                if k.as_str() == Some("$ref") {
                    if let Value::Str(s) = v {
                        out.push((path.clone(), s.clone()));
                    }
                } else if v.is_mapping() || v.is_sequence() {
                    let mut child_path = path.clone();
                    if let Some(key) = k.as_str() {
                        child_path.push(crate::path::PathPart::Key(key.to_string()));
                    }
                    reference_iterator_impl(v, &child_path, out)?;
                }
            }
        }
        Value::Array(items) => {
            for (idx, item) in items.iter().enumerate() {
                if item.is_mapping() || item.is_sequence() {
                    let mut child_path = path.clone();
                    child_path.push(crate::path::PathPart::Index(idx));
                    reference_iterator_impl(item, &child_path, out)?;
                }
            }
        }
        _ => {}
    }
    Ok(())
}

pub fn collect_external_resources(
    value: &Value,
    base_url: Option<&ParsedUrl>,
    resolve_types: u32,
) -> Result<Vec<ParsedUrl>, PranceError> {
    let mut urls = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for (_, refstring) in reference_iterator(value, &Vec::new())? {
        let (ref_url, _) = split_reference(base_url, &refstring)?;
        if skip_reference(base_url, &ref_url, resolve_types)? {
            continue;
        }
        let resource = urlresource(&ref_url);
        if seen.insert(resource) {
            urls.push(ref_url);
        }
    }
    Ok(urls)
}
