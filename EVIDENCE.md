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

