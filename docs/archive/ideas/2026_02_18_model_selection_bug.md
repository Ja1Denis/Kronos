# Debugging Model Selection in Kronos

## Problem Description
Despite specifying `client_model="gemini-3-pro"` in `kronos_query`, the system calculates savings and ROI based on `gemini-3-flash` pricing, as evidenced by the "Kronos Efficiency Report" footer and CLI stats.

## Observations
- The user executed a query with explicit `client_model='gemini-3-pro'`.
- The output report explicitly stated: `Kronos Efficiency Report (GEMINI-3-FLASH Optimized)`.
- The CLI stats (`kronos_stats`) only show savings for `gemini-3-flash`.

## Initial Hypothesis
The `ContextComposer` or `BudgetConfig` likely has a hardcoded default or missing pricing keys for newer models like `gemini-3-pro`, causing it to fallback to `gemini-3-flash` (or old `gemini-1.5-flash`).

## Investigation Plan
1.  **Inspect `src/modules/context_budgeter.py`**: Check the `pricing` dictionary and model mappings.
2.  **Verify Parameter Flow**: Trace `client_model` from `mcp_server.py` -> `kronos_query` -> `ContextComposer`.
3.  **Update Lookups**: Add missing model keys if necessary.
4.  **Verify Fix**: Run another test query with `gemini-3-pro` and check if stats update correctly.

## Status
- [ ] Inspect Code
- [ ] Identify Missing Keys
- [ ] Implement Fix
- [ ] Verify
