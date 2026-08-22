# Evidence

One proof per Definition of Done box, a test name with its output, a log line, or a curl transcript. Filled in as each phase completes.

## Constraint profiles enforced by code

Nine deterministic tests covering length, hashtags, banned phrases, shouting, missing source URL, and cross-platform profile differences.

```
$ pytest -v
collected 9 items

tests/test_validator.py::test_valid_variant_passes PASSED
tests/test_validator.py::test_variant_too_long_is_blocked PASSED
tests/test_validator.py::test_variant_too_short_is_blocked PASSED
tests/test_validator.py::test_variant_too_many_hashtags_is_blocked PASSED
tests/test_validator.py::test_banned_phrase_is_blocked PASSED
tests/test_validator.py::test_shouting_is_blocked PASSED
tests/test_validator.py::test_missing_source_url_is_blocked PASSED
tests/test_validator.py::test_url_does_not_inflate_sentence_count PASSED
tests/test_validator.py::test_same_text_passes_x_but_fails_linkedin PASSED

9 passed in 0.64s
```

## Ingestion

A post enters as URL or Markdown and is stored. Generation reads only the stored post.

POST /posts with pasted markdown → 201, stored with the given title.
POST /posts with only source_url → 201, page fetched and text extracted.
POST /posts with a blocked page → 422 "Page returned 403."
POST /posts with a thin page → 422 "Could not extract enough text from the page."

Tests: test_fetch_rejects_unreachable_host

## Variant generation

One stored post produces different variants per platform, each passing its constraint profile.

POST /campaigns/1/variants → 3 variants created (discord, x, linkedin), failed: {}
Second call to the same endpoint → created: [], skipped: [discord, x, linkedin]

Tests: test_template_generator_produces_different_variants,
test_template_variants_include_source_url

## Resilience: AI failure falls back to templates

When Gemini is unavailable the generator returns template output instead of failing.
Verified live twice: a retired model name (404) and a free-tier quota limit (429).
Both times all three variants were produced from templates with no crash.

Tests: test_falls_back_to_template_without_api_key

```
$ pytest -v
collected 15 items

tests/test_fetcher.py::test_fetch_rejects_unreachable_host PASSED 
tests/test_generator.py::test_template_generator_produces_different_variants PASSED 
tests/test_generator.py::test_template_variants_include_source_url PASSED 
tests/test_generator.py::test_falls_back_to_template_without_api_key PASSED 
tests/test_generator.py::test_prompt_includes_platform_rules PASSED 
tests/test_generator.py::test_prompt_includes_previous_errors_on_retry PASSED 
tests/test_validator.py::test_valid_variant_passes PASSED 
tests/test_validator.py::test_variant_too_long_is_blocked PASSED 
tests/test_validator.py::test_variant_too_short_is_blocked PASSED  
tests/test_validator.py::test_variant_too_many_hashtags_is_blocked PASSED 
tests/test_validator.py::test_banned_phrase_is_blocked PASSED 
tests/test_validator.py::test_shouting_is_blocked PASSED 
tests/test_validator.py::test_missing_source_url_is_blocked PASSED 
tests/test_validator.py::test_url_does_not_inflate_sentence_count PASSED 
tests/test_validator.py::test_same_text_passes_x_but_fails_linkedin PASSED 

15 Passed in 1.71s
```