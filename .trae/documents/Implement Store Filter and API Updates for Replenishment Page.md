# Implementation Plan for Replenishment Page Enhancements

## 1. Add Store Filter UI Component

* Add a filter section similar to forecast.vue

* Include store selection dropdown using uni-data-select

* Add necessary UI elements and styles

* Ensure responsive design for different screen sizes

## 2. Add Filter Data Properties

* Add `filters` object with storeId, dateRange, dcId, ecdcId, skuId, and status

* Add `storeOptions` array with store choices

* Add other filter options as needed

* Import necessary utilities from api.js

## 3. Update onLoad Method

* Use `getSelectedStore()` to get the currently selected store

* Set `filters.storeId` to the selected store's ID

* Set `filters.ecdcId` for compatibility

* Initialize date range and other filters

## 4. Update fetchReplenishment Method

* Add store\_id parameter to API request

* Update API endpoint to use `/api/planning/replenishment`

* Include other filter parameters

* Handle loading and error states

## 5. Add Adjustment and Approval Functionality

* Add methods for plan adjustment (PUT /api/planning/replenishment/{plan\_id}/adjust)

* Add methods for plan approval/rejection (PUT /api/planning/replenishment/{plan\_id}/approve)

* Add modal dialogs for user input

* Update UI to include action buttons

## 6. Update UI Components

* Add action buttons for adjusting and approving plans

* Add modal dialogs for quantity adjustment and approval

* Update status display and styling

* Add confirmation messages for user actions

## 7. Testing and Validation

* Ensure all API endpoints are correctly updated

* Test store filter functionality

* Test default store selection

* Test adjustment and approval workflows

* Verify no lint or type errors

## Key Changes

* Add store filter similar to forecast.vue

* Set default store from index.vue selection

* Update all API endpoints to use /api/planning/replenishment

* Implement full CRUD-like operations for replenishment plans

* Ensure responsive design and user-friendly interface

