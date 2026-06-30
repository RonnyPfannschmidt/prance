use std::collections::{HashSet, VecDeque};

use pyo3::prelude::*;
use rayon::prelude::*;

use crate::error::PranceError;
use crate::fetch::{DocumentCache, fetch_url};
use crate::resolver::{ResolveOptions, collect_external_resources};
use crate::url::{ParsedUrl, urlresource};
use crate::value::Value;

pub fn prefetch_external_documents(
    root: &Value,
    base_url: Option<&ParsedUrl>,
    opts: &ResolveOptions,
    threshold: usize,
    cache: &DocumentCache,
    py: Python<'_>,
) -> Result<(), PranceError> {
    if let Some(ref url) = base_url {
        let key = crate::fetch::CacheKey {
            resource: urlresource(url),
            strict: opts.strict,
        };
        if cache.get_document(&key).is_none() {
            cache.insert_document(key, root.deep_copy());
        }
    }

    let mut discovered: HashSet<String> = HashSet::new();
    let mut queue: VecDeque<ParsedUrl> = VecDeque::new();

    enqueue_external(root, base_url, opts.resolve_types, &mut discovered, &mut queue)?;

    while !queue.is_empty() {
        let batch: Vec<ParsedUrl> = queue.drain(..).collect();

        if batch.len() < threshold {
            for url in &batch {
                prefetch_one(py, cache, url, opts)?;
            }
        } else {
            let errors: Vec<PranceError> = py.allow_threads(|| {
                batch
                    .par_iter()
                    .filter_map(|url| {
                        Python::with_gil(|py| prefetch_one(py, cache, url, opts).err())
                    })
                    .collect()
            });
            if let Some(err) = errors.into_iter().next() {
                return Err(err);
            }
        }

        for url in batch {
            let key = crate::fetch::CacheKey {
                resource: urlresource(&url),
                strict: opts.strict,
            };
            if let Some(doc) = cache.get_document(&key) {
                enqueue_external(
                    &doc,
                    Some(&url),
                    opts.resolve_types,
                    &mut discovered,
                    &mut queue,
                )?;
            }
        }
    }

    Ok(())
}

fn enqueue_external(
    value: &Value,
    base_url: Option<&ParsedUrl>,
    resolve_types: u32,
    discovered: &mut HashSet<String>,
    queue: &mut VecDeque<ParsedUrl>,
) -> Result<(), PranceError> {
    for url in collect_external_resources(value, base_url, resolve_types)? {
        let resource = urlresource(&url);
        if discovered.insert(resource) {
            queue.push_back(url);
        }
    }
    Ok(())
}

fn prefetch_one(
    py: Python<'_>,
    cache: &DocumentCache,
    url: &ParsedUrl,
    opts: &ResolveOptions,
) -> Result<(), PranceError> {
    let key = crate::fetch::CacheKey {
        resource: urlresource(url),
        strict: opts.strict,
    };
    if cache.get_document(&key).is_some() {
        return Ok(());
    }
    let _ = fetch_url(
        py,
        url,
        cache,
        opts.encoding.as_deref(),
        opts.strict,
    )?;
    Ok(())
}

pub fn build_cache_with_root(
    root: &Value,
    base_url: Option<&ParsedUrl>,
    strict: bool,
    pool: std::sync::Arc<std::sync::Mutex<crate::convert::OpaquePool>>,
) -> DocumentCache {
    let cache = DocumentCache::new(pool);
    if let Some(url) = base_url {
        cache.insert_document(
            crate::fetch::CacheKey {
                resource: urlresource(&url),
                strict,
            },
            root.deep_copy(),
        );
    }
    cache
}
