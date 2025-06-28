# Issue #60: Merge Duplicate Factory Implementations

**GitHub Issue:** https://github.com/[owner]/[repo]/issues/60

## Problem Description

The Starfish codebase currently has two factory implementations with overlapping functionality:
- `src/starfish/data_factory/factory.py` - Contains the `@data_factory` decorator interface and high-level API (113 lines)
- `src/starfish/data_factory/factory_.py` - Contains the main `Factory` class implementation (547 lines, 20+ methods)

This duplication creates:
- Developer confusion about which file to modify
- Increased maintenance burden  
- No clear single source of truth
- Potential for divergent implementations over time

## Analysis

### Current Structure
- `factory.py`: Public API with `data_factory` decorator, imports `Factory` from `factory_.py`
- `factory_.py`: Core `Factory` class implementation + `_default_input_converter` helper

### Import Dependencies Found
**Files importing from `factory.py`:**
- `src/starfish/__init__.py` (line 9)
- Multiple test files (7 files total)

**Files importing from `factory_.py`:**
- `src/starfish/data_factory/factory_wrapper.py` (line 12)
- `src/starfish/data_factory/factory_executor_manager.py` (line 9) 
- `src/starfish/data_factory/factory.py` (line 5)

## Consolidation Plan

### Approach: Merge into `factory.py`
- Keep `factory.py` as the single source file since it already contains the public API
- Move `Factory` class and `_default_input_converter` from `factory_.py` into `factory.py`
- Update 3 source files that import from `factory_.py`
- Remove `factory_.py`
- No test changes needed (all tests import from `factory.py`)

### Implementation Steps

1. **Create feature branch for issue #60**

2. **Merge content into factory.py:**
   - Add `Factory` class from `factory_.py` to `factory.py`
   - Add `_default_input_converter` function to `factory.py`
   - Remove import of Factory from `factory_.py`
   - Add proper `__all__` exports

3. **Update import statements:**
   - `factory_wrapper.py`: Change import to use `factory` instead of `factory_`
   - `factory_executor_manager.py`: Change import to use `factory` instead of `factory_`

4. **Remove duplicate file:**
   - Delete `factory_.py`

5. **Test and validate:**
   - Run test suite to ensure all functionality preserved
   - Check all imports work correctly
   - Verify no breaking changes

6. **Create pull request**

## Acceptance Criteria Verification

✅ **Single Source File**: Only `factory.py` will exist after completion
✅ **Backward Compatibility**: All existing public APIs continue to work
✅ **Test Compatibility**: All existing tests pass (no import changes needed for tests)
✅ **Import Consistency**: Only 3 source files need import updates
✅ **Functionality Preservation**: No existing functionality altered
✅ **Clean Exports**: Module will define public interface via `__all__`
✅ **Documentation**: Module will have clear docstrings

## Risk Assessment
- **Low Risk**: Small scope (3 file import changes)
- **No Test Impact**: Tests only import from `factory.py` 
- **No Public API Changes**: All public interfaces remain the same
- **Reversible**: Changes can be easily reverted if issues arise

## Notes
- Previous factory reorganization PRs (#38, #39) were merged, indicating team support for factory consolidation
- Implementation preserves all existing functionality without modification
- Clean separation between public API (decorator) and implementation (class) maintained within single file