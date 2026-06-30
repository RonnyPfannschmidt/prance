use std::collections::HashMap;
use std::path::{Component, Path, PathBuf};
use std::sync::{LazyLock, Mutex};

use pyo3::prelude::*;
use pyo3::types::PyTuple;
use url::Url;

use crate::error::PranceError;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ParsedUrl {
    pub scheme: String,
    pub netloc: String,
    pub path: String,
    pub params: String,
    pub query: String,
    pub fragment: String,
}

impl ParsedUrl {
    pub fn geturl(&self) -> String {
        if self.scheme == "file" || (self.scheme.is_empty() && self.path.starts_with('/')) {
            return format!("file://{}", self.path);
        }
        let mut url = String::new();
        if !self.scheme.is_empty() {
            url.push_str(&self.scheme);
            url.push(':');
        }
        if !self.netloc.is_empty() {
            url.push_str("//");
            url.push_str(&self.netloc);
        }
        url.push_str(&self.path);
        if !self.params.is_empty() {
            url.push(';');
            url.push_str(&self.params);
        }
        if !self.query.is_empty() {
            url.push('?');
            url.push_str(&self.query);
        }
        if !self.fragment.is_empty() {
            url.push('#');
            url.push_str(&self.fragment);
        }
        url
    }

    pub fn to_py_parse_result(&self, py: Python<'_>) -> PyResult<PyObject> {
        let urllib = py.import("urllib.parse")?;
        let parse_result = urllib.getattr("ParseResult")?;
        let tuple = PyTuple::new(
            py,
            [
                self.scheme.as_str(),
                self.netloc.as_str(),
                self.path.as_str(),
                self.params.as_str(),
                self.query.as_str(),
                self.fragment.as_str(),
            ],
        )?;
        Ok(parse_result.call1(tuple)?.into())
    }
}

impl From<Url> for ParsedUrl {
    fn from(url: Url) -> Self {
        Self {
            scheme: url.scheme().to_string(),
            netloc: url
                .host_str()
                .map(|h| {
                    if let Some(port) = url.port() {
                        format!("{h}:{port}")
                    } else {
                        h.to_string()
                    }
                })
                .unwrap_or_default(),
            path: url.path().to_string(),
            params: String::new(),
            query: url.query().unwrap_or("").to_string(),
            fragment: url.fragment().unwrap_or("").to_string(),
        }
    }
}

static URLRESOURCE_CACHE: LazyLock<Mutex<HashMap<(String, String, String), String>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

pub fn urlresource(url: &ParsedUrl) -> String {
    let key = (url.scheme.clone(), url.netloc.clone(), url.path.clone());
    if let Ok(cache) = URLRESOURCE_CACHE.lock() {
        if let Some(v) = cache.get(&key) {
            return v.clone();
        }
    }
    let mut u = url.clone();
    u.params.clear();
    u.query.clear();
    u.fragment.clear();
    let result = u.geturl();
    if let Ok(mut cache) = URLRESOURCE_CACHE.lock() {
        cache.insert(key, result.clone());
    }
    result
}

pub fn is_pathname_valid(pathname: &str) -> bool {
    if pathname.is_empty() {
        return false;
    }
    if pathname.contains('\0') {
        return false;
    }
    Path::new(pathname).components().all(|c| match c {
        Component::Normal(_) | Component::RootDir | Component::Prefix(_) => true,
        Component::ParentDir | Component::CurDir => true,
    })
}

pub fn from_posix(fname: &str) -> String {
    #[cfg(windows)]
    {
        let mut s = fname.to_string();
        if s.starts_with('/') {
            s = s[1..].to_string();
        }
        s.replace('/', "\\")
    }
    #[cfg(not(windows))]
    {
        fname.to_string()
    }
}

pub fn to_posix(fname: &str) -> String {
    #[cfg(windows)]
    {
        let mut s = fname.replace('\\', "/");
        if Path::new(fname).is_absolute() && !s.starts_with('/') {
            s = format!("/{s}");
        }
        s
    }
    #[cfg(not(windows))]
    {
        fname.to_string()
    }
}

fn lexical_normalize(path: PathBuf) -> PathBuf {
    let mut out = PathBuf::new();
    for component in path.components() {
        match component {
            Component::Prefix(prefix) => out.push(prefix.as_os_str()),
            Component::RootDir => out.push(component.as_os_str()),
            Component::CurDir => {}
            Component::ParentDir => {
                let mut poppable = false;
                for existing in out.components().rev() {
                    match existing {
                        Component::Normal(_) => {
                            poppable = true;
                            break;
                        }
                        Component::RootDir | Component::Prefix(_) => break,
                        Component::CurDir | Component::ParentDir => {}
                    }
                }
                if poppable {
                    out.pop();
                }
            }
            Component::Normal(part) => out.push(part),
            _ => {}
        }
    }
    out
}

fn strip_trailing_separator(path: PathBuf) -> PathBuf {
    let mut s = path.to_string_lossy().into_owned();
    while s.len() > 1 && (s.ends_with('/') || (cfg!(windows) && s.ends_with('\\'))) {
        s.pop();
    }
    PathBuf::from(s)
}

pub fn canonical_filename(filename: &str) -> String {
    let path = from_posix(filename);
    let mut p = strip_trailing_separator(lexical_normalize(PathBuf::from(&path)));
    loop {
        match p.canonicalize() {
            Ok(canonical) => p = canonical,
            Err(_) => break,
        }
        match std::fs::read_link(&p) {
            Ok(link) => {
                if let Some(parent) = p.parent() {
                    p = parent.join(link);
                } else {
                    p = link;
                }
            }
            Err(_) => break,
        }
    }
    to_posix(p.to_string_lossy().as_ref())
}

pub fn abspath(filename: &str, relative_to: Option<&str>) -> String {
    let fname = from_posix(filename);
    let mut path = PathBuf::from(&fname);
    if let Some(ref_to) = relative_to {
        if !path.is_absolute() {
            let rel = from_posix(ref_to);
            let rel_path = Path::new(&rel);
            if rel_path.is_dir() {
                path = rel_path.join(&path);
            } else if let Some(parent) = rel_path.parent() {
                path = parent.join(&path);
            }
        }
    }
    canonical_filename(path.to_string_lossy().as_ref())
}

fn split_ref_fragment(url: &str) -> (String, String) {
    match url.split_once('#') {
        Some((base, frag)) => (base.to_string(), frag.to_string()),
        None => (url.to_string(), String::new()),
    }
}

fn urlparse_components(url: &str) -> Result<(String, String, String, String), PranceError> {
    let (base, fragment) = split_ref_fragment(url);
    if base.starts_with('#') || base.is_empty() {
        return Ok((String::new(), String::new(), String::new(), fragment));
    }
    if is_pathname_valid(&base) && !base.contains("://") {
        return Ok((String::new(), String::new(), to_posix(&base), fragment));
    }
    if base.starts_with("file://") {
        let parsed = Url::parse(&base).map_err(|_| {
            PranceError::Resolution(format!("Unable to parse url: {url}"))
        })?;
        return Ok((
            parsed.scheme().to_string(),
            String::new(),
            parsed.path().to_string(),
            fragment,
        ));
    }
    let parsed = Url::parse(&base).map_err(|_| {
        PranceError::Resolution(format!("Unable to parse url: {url}"))
    })?;
    let netloc = parsed
        .host_str()
        .map(|h| {
            if let Some(port) = parsed.port() {
                format!("{h}:{port}")
            } else {
                h.to_string()
            }
        })
        .unwrap_or_default();
    Ok((
        parsed.scheme().to_string(),
        netloc,
        parsed.path().to_string(),
        fragment,
    ))
}

fn components_to_parsed(
    scheme: String,
    netloc: String,
    path: String,
    fragment: String,
) -> ParsedUrl {
    ParsedUrl {
        scheme,
        netloc,
        path,
        params: String::new(),
        query: String::new(),
        fragment,
    }
}

pub fn absurl(url: &str, relative_to: Option<&str>) -> Result<ParsedUrl, PranceError> {
    let (mut scheme, mut netloc, mut path, mut fragment) = urlparse_components(url)?;

    if !scheme.is_empty() && scheme != "file" {
        return Ok(components_to_parsed(scheme, netloc, path, fragment));
    }

    let reference = if let Some(rel) = relative_to {
        Some(urlparse_components(rel)?)
    } else {
        None
    };

    if path.is_empty() {
        let (ref_scheme, ref_netloc, ref_path, _) = reference.ok_or_else(|| {
            PranceError::Resolution(
                "Cannot build an absolute file URL from a fragment without a reference with path!"
                    .into(),
            )
        })?;
        if ref_path.is_empty() {
            return Err(PranceError::Resolution(
                "Cannot build an absolute file URL from a fragment without a reference with path!"
                    .into(),
            ));
        }
        scheme = if ref_scheme.is_empty() {
            "file".into()
        } else {
            ref_scheme
        };
        netloc = ref_netloc;
        path = ref_path;
    } else if Path::new(from_posix(&path).as_str()).is_absolute() {
        if scheme.is_empty() {
            scheme = "file".into();
        }
    } else {
        let (ref_scheme, _, ref_path, _) = reference.ok_or_else(|| {
            PranceError::Resolution(
                "Cannot build an absolute file URL from a relative path without a reference!"
                    .into(),
            )
        })?;
        if !ref_scheme.is_empty() && ref_scheme != "file" {
            return Err(PranceError::Resolution(
                "Cannot build an absolute file URL with a non-file reference!".into(),
            ));
        }
        scheme = "file".into();
        path = abspath(&path, Some(&ref_path));
    }

    Ok(components_to_parsed(scheme, netloc, path, fragment))
}

fn normalize_fragment_path(obj_path: &[String]) -> Vec<String> {
    obj_path
        .iter()
        .map(|p| p.replace("~1", "/").replace("~0", "~"))
        .collect()
}

pub fn split_fragment_reference(
    base_url: Option<&ParsedUrl>,
    reference: &str,
) -> Option<(ParsedUrl, Vec<String>)> {
    if !reference.starts_with('#') {
        return None;
    }
    let base = base_url?;
    let fragment = &reference[1..];
    let mut obj_path: Vec<String> = fragment.split('/').map(String::from).collect();
    while obj_path.first().map(|s| s.is_empty()).unwrap_or(false) {
        obj_path.remove(0);
    }
    let obj_path = normalize_fragment_path(&obj_path);
    Some((base.clone(), obj_path))
}

pub fn split_url_reference(
    base_url: Option<&ParsedUrl>,
    reference: &str,
) -> Result<(ParsedUrl, Vec<String>), PranceError> {
    if let Some(result) = split_fragment_reference(base_url, reference) {
        return Ok(result);
    }
    let rel = base_url.map(|u| u.geturl());
    let parsed = absurl(reference, rel.as_deref())?;
    let mut obj_path: Vec<String> = parsed.fragment.split('/').map(String::from).collect();
    while obj_path.first().map(|s| s.is_empty()).unwrap_or(false) {
        obj_path.remove(0);
    }
    let obj_path = normalize_fragment_path(&obj_path);
    let mut url = parsed;
    url.fragment.clear();
    Ok((url, obj_path))
}
