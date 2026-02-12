# Coding Guidelines for Kronos Pointer System

## MANDATORY: Defense in Depth

Every function that processes external input MUST:

1. **Type Check First**
   - Never assume input type.
   - Use `isinstance()` explicitly for all critical arguments.
   - Reject `None`, empty strings, or invalid types immediately.

2. **Validate Before Use**
   - **File paths**: Always check for path traversal using `is_safe_path()`.
   - **Line ranges**: Always check bounds using `validate_line_range()`.
   - **Strings**: Check for null bytes (`\x00`), newlines in paths, and excessive length.

3. **Handle Errors Gracefully**
   - Wrap every file operation (I/O) in `try-except`.
   - Assume every external API call or database query can fail.
   - Log errors/warnings clearly, but avoid crashing the main process.

4. **Never Trust Data**
   - Assume ChromaDB metadata can be `None` or corrupt.
   - Assume lists returned from search can be empty.
   - Use `.get(key, default)` instead of direct access `[key]`.

## FORBIDDEN Patterns

❌ `result['key']` - **Never** use direct key access on external data. Use `result.get('key', default)`.
❌ `list[0]` - **Never** assume a list has elements. Check `if len(list) > 0` first.
❌ `open(user_path)` - **Never** open a path provided by a user/query without `is_safe_path`.
❌ `print(e)` - Use proper logging or colored output for system status.
❌ `assert` for production logic - Use `assert` only for internal invariants; use `if/raise` or `return error` for input validation.

## REQUIRED Patterns

✅ **Type checks**: `if not isinstance(x, expected_type): return None`
✅ **Null checks**: `if x is None: ...`
✅ **Bounds checks**: `if 0 <= index < len(list): ...`
✅ **Try-except**: Around every I/O, network, or complex parsing operation.
✅ **Logging**: Use `logger` or colored console prints for visibility.

## Test Requirements

Every new core function MUST have tests covering:
- **Happy path**: Normal valid input.
- **Empty input**: `""`, `[]`, `{}`.
- **None input**: `None`.
- **Invalid type**: Passing `123` where `str` is expected.
- **Boundary conditions**: Correct indices, max/min values.
- **Error conditions**: File not found, permission denied.

---
*Ove smjernice su obvezne za sve buduće nadogradnje Kronos sustava.*
