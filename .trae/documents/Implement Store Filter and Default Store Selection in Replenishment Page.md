## Implementation Plan

### 1. Add Store Filter to Replenishment Page
- **Add store filter UI** similar to forecast.vue: add a `uni-data-select` component for store selection in the filter section
- **Add storeOptions data** to store the list of available stores
- **Add storeId to filters** object to track selected store
- **Add @change event** to trigger data refresh when store selection changes

### 2. Set Default Store from Selected Store
- **Import getSelectedStore** function from api.js
- **Set default store** in the onLoad method: if a store is selected in index.vue, use it as the default value for storeId
- **Ensure ECDC ID fallback** still works for backward compatibility

### 3. Update API Call to Include Store Filter
- **Modify fetchReplenishment method** to include store_id parameter when calling the API
- **Update API endpoint** to use the correct /api/planning/replenishment path

### 4. Verify Functionality
- **Test store filter** functionality by selecting different stores
- **Test default store** behavior by selecting a store in index.vue and navigating to replenishment page
- **Test API calls** to ensure all endpoints work correctly
- **Test plan management** functions (approve, reject, adjust) to ensure they still work

### 5. Code Quality Check
- **Run linting** to ensure code quality
- **Verify no type errors** in the code

## Expected Changes

### Files to Modify
1. **frontend/pages/index/replenishment.vue**
   - Add store filter UI
   - Add storeOptions data
   - Update filters object
   - Update onLoad method
   - Update fetchReplenishment method

### Key Changes
- Store filter will be added as a new filter item in the filter section
- Default store will be set based on the selected store from index.vue
- API calls will include the store_id parameter when a store is selected
- All existing functionality (approve, reject, adjust) will be preserved