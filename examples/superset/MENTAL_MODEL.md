# MENTAL_MODEL — superset

> How to think about this codebase. v0.1 emits a deterministic skeleton from structure and history; v0.2 will enrich it with LLM synthesis.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise (DEC-015).

## At a glance

- A **Typescript** codebase of 3,862 source file(s).
- 50 contributor(s) over ~10.9 years.

## Likely entry points

_Confidence: `INFERRED` (DEC-015)._

Files whose names conventionally mark an entry point (stem matches `main` / `app` / `cli` / `index` / `__main__` / `server` / `run` / `manage`):

- `docs/src/pages/index.tsx`
- `docs/src/theme/ApiExplorer/MethodEndpoint/index.tsx`
- `docs/src/theme/DocVersionBadge/index.js`
- `docs/src/theme/Playground/Preview/index.tsx`
- `docs/src/theme/ReactLiveScope/index.tsx`
- `superset-embedded-sdk/src/index.ts`
- `superset-extensions-cli/src/superset_extensions_cli/cli.py`
- `superset-frontend/cypress-base/cypress/utils/index.ts`
- `superset-frontend/eslint-rules/eslint-plugin-i18n-strings/index.ts`
- `superset-frontend/eslint-rules/eslint-plugin-icons/index.ts`
- `superset-frontend/eslint-rules/eslint-plugin-theme-colors/index.ts`
- `superset-frontend/packages/generator-superset/generators/app/index.js`
- `superset-frontend/packages/generator-superset/generators/plugin-chart/index.js`
- `superset-frontend/packages/superset-core/src/commands/index.ts`
- `superset-frontend/packages/superset-core/src/common/index.ts`
- `superset-frontend/packages/superset-core/src/components/Alert/index.tsx`
- `superset-frontend/packages/superset-core/src/contributions/index.ts`
- `superset-frontend/packages/superset-core/src/editors/index.ts`
- `superset-frontend/packages/superset-core/src/menus/index.ts`
- `superset-frontend/packages/superset-core/src/sqlLab/index.ts`
- `superset-frontend/packages/superset-core/src/theme/index.tsx`
- `superset-frontend/packages/superset-core/src/theme/utils/index.ts`
- `superset-frontend/packages/superset-core/src/translation/types/index.ts`
- `superset-frontend/packages/superset-core/src/views/index.ts`
- `superset-frontend/packages/superset-ui-core/src/components/ActionButton/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/AsyncAceEditor/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/AsyncEsmComponent/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Avatar/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Badge/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Button/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/ButtonGroup/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/CachedLabel/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/CertifiedBadge/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/CodeEditor/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/CodeSyntaxHighlighter/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/ColorPicker/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/ConfirmModal/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/ConfirmStatusChange/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/CronPicker/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/DatePicker/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/DeleteModal/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Divider/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Dropdown/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/DropdownButton/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/DynamicEditableTitle/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/EditableTitle/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/EmptyState/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/FaveStar/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Flex/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/IconButton/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Icons/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/InfoTooltip/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Label/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/LastUpdated/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/List/index.ts`
- `superset-frontend/packages/superset-ui-core/src/components/ListViewCard/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Loading/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Menu/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Metadata/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/ModalTrigger/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/PageHeaderWithActions/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Pagination/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Popconfirm/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Popover/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/PopoverDropdown/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/PopoverSection/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Progress/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/ProgressBar/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Radio/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/RefreshLabel/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Slider/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Table/cell-renderers/ActionCell/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Table/cell-renderers/BooleanCell/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Table/cell-renderers/ButtonCell/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Table/cell-renderers/NullCell/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Table/cell-renderers/NumericCell/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Table/cell-renderers/TimeCell/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Table/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/TableCollection/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/TelemetryPixel/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/ThemedAgGridReact/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Timer/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/TimezoneSelector/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/TooltipParagraph/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/TruncatedList/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/Typography/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/UnsavedChangesModal/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/components/WarningIconWithTooltip/index.tsx`
- `superset-frontend/packages/superset-ui-core/src/math-expression/index.ts`
- `superset-frontend/packages/superset-ui-core/src/query/api/v1/index.ts`
- `superset-frontend/packages/superset-ui-core/src/types/index.ts`
- `superset-frontend/plugins/legacy-plugin-chart-calendar/src/index.ts`
- `superset-frontend/plugins/legacy-plugin-chart-chord/src/index.ts`
- `superset-frontend/plugins/legacy-plugin-chart-country-map/src/index.ts`
- `superset-frontend/plugins/legacy-plugin-chart-horizon/src/index.ts`
- `superset-frontend/plugins/legacy-plugin-chart-paired-t-test/src/index.ts`
- `superset-frontend/plugins/legacy-plugin-chart-parallel-coordinates/src/index.ts`
- `superset-frontend/plugins/legacy-plugin-chart-partition/src/index.ts`
- `superset-frontend/plugins/legacy-plugin-chart-rose/src/index.ts`
- `superset-frontend/plugins/legacy-plugin-chart-world-map/src/index.ts`
- `superset-frontend/plugins/legacy-preset-chart-nvd3/src/Bubble/index.ts`
- `superset-frontend/plugins/legacy-preset-chart-nvd3/src/Bullet/index.ts`
- `superset-frontend/plugins/legacy-preset-chart-nvd3/src/Compare/index.ts`
- `superset-frontend/plugins/legacy-preset-chart-nvd3/src/TimePivot/index.ts`
- `superset-frontend/plugins/plugin-chart-ag-grid-table/src/AgGridTable/index.tsx`
- `superset-frontend/plugins/plugin-chart-ag-grid-table/src/index.ts`
- `superset-frontend/plugins/plugin-chart-ag-grid-table/src/styles/index.tsx`
- `superset-frontend/plugins/plugin-chart-cartodiagram/src/plugin/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/BigNumber/BigNumberPeriodOverPeriod/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/BigNumber/BigNumberTotal/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/BigNumber/BigNumberWithTrendline/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/BoxPlot/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Bubble/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Funnel/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Gantt/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Gauge/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Graph/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Heatmap/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Histogram/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/MixedTimeseries/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Pie/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Radar/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Sankey/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Sunburst/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Timeseries/Area/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Timeseries/Regular/Bar/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Timeseries/Regular/Line/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Timeseries/Regular/Scatter/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Timeseries/Regular/SmoothLine/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Timeseries/Step/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Timeseries/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Tree/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Treemap/index.ts`
- `superset-frontend/plugins/plugin-chart-echarts/src/Waterfall/index.ts`
- `superset-frontend/plugins/plugin-chart-handlebars/src/plugin/index.ts`
- `superset-frontend/plugins/plugin-chart-pivot-table/src/plugin/index.ts`
- `superset-frontend/plugins/plugin-chart-point-cluster-map/src/index.ts`
- `superset-frontend/plugins/plugin-chart-table/src/index.ts`
- `superset-frontend/plugins/plugin-chart-word-cloud/src/plugin/controls/ColorSchemeControl/index.tsx`
- `superset-frontend/plugins/plugin-chart-word-cloud/src/plugin/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/Multi/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/layers/Arc/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/layers/Contour/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/layers/Geojson/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/layers/Grid/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/layers/Heatmap/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/layers/Hex/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/layers/Path/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/layers/Polygon/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/layers/Scatter/index.ts`
- `superset-frontend/plugins/preset-chart-deckgl/src/layers/Screengrid/index.ts`
- `superset-frontend/src/SqlLab/components/App/index.tsx`
- `superset-frontend/src/SqlLab/components/AppLayout/index.tsx`
- `superset-frontend/src/SqlLab/components/ColumnElement/index.tsx`
- `superset-frontend/src/SqlLab/components/EditorAutoSync/index.tsx`
- `superset-frontend/src/SqlLab/components/EditorWrapper/index.tsx`
- `superset-frontend/src/SqlLab/components/EstimateQueryCostButton/index.tsx`
- `superset-frontend/src/SqlLab/components/ExploreCtasResultsButton/index.tsx`
- `superset-frontend/src/SqlLab/components/ExploreResultsButton/index.tsx`
- `superset-frontend/src/SqlLab/components/HighlightedSql/index.tsx`
- `superset-frontend/src/SqlLab/components/KeyboardShortcutButton/index.tsx`
- `superset-frontend/src/SqlLab/components/PopEditorTab/index.tsx`
- `superset-frontend/src/SqlLab/components/QueryAutoRefresh/index.tsx`
- `superset-frontend/src/SqlLab/components/QueryHistory/index.tsx`
- `superset-frontend/src/SqlLab/components/QueryLimitSelect/index.tsx`
- `superset-frontend/src/SqlLab/components/QueryStateLabel/index.tsx`
- `superset-frontend/src/SqlLab/components/QueryStatusBar/index.tsx`
- `superset-frontend/src/SqlLab/components/QueryTable/index.tsx`
- `superset-frontend/src/SqlLab/components/ResultSet/index.tsx`
- `superset-frontend/src/SqlLab/components/RunQueryActionButton/index.tsx`
- `superset-frontend/src/SqlLab/components/SaveDatasetActionButton/index.tsx`
- `superset-frontend/src/SqlLab/components/SaveDatasetModal/index.tsx`
- `superset-frontend/src/SqlLab/components/SaveQuery/index.tsx`
- `superset-frontend/src/SqlLab/components/ScheduleQueryButton/index.tsx`
- `superset-frontend/src/SqlLab/components/ShareSqlLabQuery/index.tsx`
- `superset-frontend/src/SqlLab/components/ShowSQL/index.tsx`
- `superset-frontend/src/SqlLab/components/SouthPane/index.tsx`
- `superset-frontend/src/SqlLab/components/SqlEditor/index.tsx`
- `superset-frontend/src/SqlLab/components/SqlEditorLeftBar/index.tsx`
- `superset-frontend/src/SqlLab/components/SqlEditorTabHeader/index.tsx`
- `superset-frontend/src/SqlLab/components/SqlEditorTopBar/index.tsx`
- `superset-frontend/src/SqlLab/components/StatusBar/index.tsx`
- `superset-frontend/src/SqlLab/components/TabbedSqlEditors/index.tsx`
- `superset-frontend/src/SqlLab/components/TableElement/index.tsx`
- `superset-frontend/src/SqlLab/components/TableExploreTree/index.tsx`
- `superset-frontend/src/SqlLab/components/TablePreview/index.tsx`
- `superset-frontend/src/SqlLab/components/TemplateParamsEditor/index.tsx`
- `superset-frontend/src/SqlLab/hooks/useQueryEditor/index.ts`
- `superset-frontend/src/chartCustomizations/components/DeckglLayerVisibility/index.ts`
- `superset-frontend/src/chartCustomizations/components/DynamicGroupBy/index.ts`
- `superset-frontend/src/chartCustomizations/components/TimeColumn/index.ts`
- `superset-frontend/src/chartCustomizations/components/TimeGrain/index.ts`
- `superset-frontend/src/components/AlteredSliceTag/index.tsx`
- `superset-frontend/src/components/AlteredSliceTag/utils/index.ts`
- `superset-frontend/src/components/AuditInfo/index.tsx`
- `superset-frontend/src/components/Chart/useDrillDetailMenuItems/index.tsx`
- `superset-frontend/src/components/CopyToClipboard/index.tsx`
- `superset-frontend/src/components/DatabaseSelector/index.tsx`
- `superset-frontend/src/components/Datasource/ChangeDatasourceModal/index.tsx`
- `superset-frontend/src/components/Datasource/DatasourceModal/index.tsx`
- `superset-frontend/src/components/Datasource/FoldersEditor/index.tsx`
- `superset-frontend/src/components/Datasource/components/CollectionTable/index.tsx`
- `superset-frontend/src/components/Datasource/components/DatasourceEditor/components/DashboardLinksExternal/index.tsx`
- `superset-frontend/src/components/Datasource/components/DatasourceEditor/components/DatasetUsageTab/index.tsx`
- `superset-frontend/src/components/Datasource/components/Field/index.tsx`
- `superset-frontend/src/components/Datasource/components/Fieldset/index.tsx`
- `superset-frontend/src/components/Datasource/utils/index.ts`
- `superset-frontend/src/components/DynamicPlugins/index.tsx`
- `superset-frontend/src/components/ErrorBoundary/index.tsx`
- `superset-frontend/src/components/FacePile/index.tsx`
- `superset-frontend/src/components/FilterableTable/index.tsx`
- `superset-frontend/src/components/GenericLink/index.tsx`
- `superset-frontend/src/components/GridTable/index.tsx`
- `superset-frontend/src/components/ImportModal/index.tsx`
- `superset-frontend/src/components/JsonModal/index.tsx`
- `superset-frontend/src/components/LastQueriedLabel/index.tsx`
- `superset-frontend/src/components/ListView/Filters/index.tsx`
- `superset-frontend/src/components/ModalTitleWithIcon/index.tsx`
- `superset-frontend/src/components/PanelToolbar/index.tsx`
- `superset-frontend/src/components/ResizableSidebar/index.tsx`
- `superset-frontend/src/components/RowCountLabel/index.tsx`
- `superset-frontend/src/components/SQLEditorWithValidation/index.tsx`
- `superset-frontend/src/components/TableSelector/index.tsx`
- `superset-frontend/src/components/Tag/index.tsx`
- `superset-frontend/src/components/TagsList/index.tsx`
- `superset-frontend/src/components/UiConfigContext/index.tsx`
- `superset-frontend/src/components/ViewListExtension/index.tsx`
- `superset-frontend/src/core/commands/index.ts`
- `superset-frontend/src/core/editors/index.ts`
- `superset-frontend/src/core/menus/index.ts`
- `superset-frontend/src/core/sqlLab/index.ts`
- `superset-frontend/src/core/views/index.ts`
- `superset-frontend/src/dashboard/components/AnchorLink/index.tsx`
- `superset-frontend/src/dashboard/components/AutoRefreshIndicator/index.tsx`
- `superset-frontend/src/dashboard/components/BuilderComponentPane/index.tsx`
- `superset-frontend/src/dashboard/components/CustomizationsBadge/index.tsx`
- `superset-frontend/src/dashboard/components/EmbeddedModal/index.tsx`
- `superset-frontend/src/dashboard/components/FiltersBadge/DetailsPanel/index.tsx`
- `superset-frontend/src/dashboard/components/FiltersBadge/FilterIndicator/index.tsx`
- `superset-frontend/src/dashboard/components/FiltersBadge/index.tsx`
- `superset-frontend/src/dashboard/components/Header/index.tsx`
- `superset-frontend/src/dashboard/components/OverwriteConfirm/index.tsx`
- `superset-frontend/src/dashboard/components/PropertiesModal/index.tsx`
- `superset-frontend/src/dashboard/components/PublishedStatus/index.tsx`
- `superset-frontend/src/dashboard/components/RefreshButton/index.tsx`
- `superset-frontend/src/dashboard/components/SliceHeader/index.tsx`
- `superset-frontend/src/dashboard/components/SliceHeaderControls/index.tsx`
- `superset-frontend/src/dashboard/components/SyncDashboardState/index.tsx`
- `superset-frontend/src/dashboard/components/URLShortLinkButton/index.tsx`
- `superset-frontend/src/dashboard/components/UndoRedoKeyListeners/index.tsx`
- `superset-frontend/src/dashboard/components/dnd/handleScroll/index.ts`
- `superset-frontend/src/dashboard/components/menu/DownloadMenuItems/index.tsx`
- `superset-frontend/src/dashboard/components/menu/ShareMenuItems/index.tsx`
- `superset-frontend/src/dashboard/components/nativeFilters/FilterBar/ActionButtons/index.tsx`
- `superset-frontend/src/dashboard/components/nativeFilters/FilterBar/CustomizationsOutOfScopeCollapsible/index.tsx`
- `superset-frontend/src/dashboard/components/nativeFilters/FilterBar/FilterBarSettings/index.tsx`
- `superset-frontend/src/dashboard/components/nativeFilters/FilterBar/FilterConfigurationLink/index.tsx`
- `superset-frontend/src/dashboard/components/nativeFilters/FilterBar/FiltersDropdownContent/index.tsx`
- `superset-frontend/src/dashboard/components/nativeFilters/FilterBar/FiltersOutOfScopeCollapsible/index.tsx`
- `superset-frontend/src/dashboard/components/nativeFilters/FilterBar/Header/index.tsx`
- `superset-frontend/src/dashboard/components/nativeFilters/FilterBar/index.tsx`
- `superset-frontend/src/dashboard/components/nativeFilters/FilterCard/index.tsx`
- `superset-frontend/src/embedded/index.tsx`
- `superset-frontend/src/explore/components/DataTableControl/index.tsx`
- `superset-frontend/src/explore/components/DatasourcePanel/DatasourcePanelDragOption/index.tsx`
- `superset-frontend/src/explore/components/DatasourcePanel/index.tsx`
- `superset-frontend/src/explore/components/ExploreChartHeader/index.tsx`
- `superset-frontend/src/explore/components/ExploreChartPanel/index.tsx`
- `superset-frontend/src/explore/components/ExploreContainer/index.tsx`
- `superset-frontend/src/explore/components/ExploreViewContainer/index.tsx`
- `superset-frontend/src/explore/components/ExportToCSVDropdown/index.tsx`
- `superset-frontend/src/explore/components/PropertiesModal/index.tsx`
- `superset-frontend/src/explore/components/RunQueryButton/index.tsx`
- `superset-frontend/src/explore/components/StashFormDataContainer/index.tsx`
- `superset-frontend/src/explore/components/controls/AnnotationLayerControl/index.tsx`
- `superset-frontend/src/explore/components/controls/CollectionControl/index.tsx`
- `superset-frontend/src/explore/components/controls/ColorBreakpointsControl/index.tsx`
- `superset-frontend/src/explore/components/controls/ColorSchemeControl/index.tsx`
- `superset-frontend/src/explore/components/controls/ColumnConfigControl/ControlForm/index.tsx`
- `superset-frontend/src/explore/components/controls/ContourControl/index.tsx`
- `superset-frontend/src/explore/components/controls/CustomListItem/index.tsx`
- `superset-frontend/src/explore/components/controls/DatasourceControl/index.tsx`
- `superset-frontend/src/explore/components/controls/FilterControl/AdhocFilter/index.ts`
- `superset-frontend/src/explore/components/controls/FilterControl/AdhocFilterControl/index.tsx`
- `superset-frontend/src/explore/components/controls/FilterControl/AdhocFilterEditPopover/index.tsx`
- `superset-frontend/src/explore/components/controls/FilterControl/AdhocFilterEditPopoverSimpleTabContent/index.tsx`
- `superset-frontend/src/explore/components/controls/FilterControl/AdhocFilterEditPopoverSqlTabContent/index.tsx`
- `superset-frontend/src/explore/components/controls/FilterControl/AdhocFilterOption/index.tsx`
- `superset-frontend/src/explore/components/controls/FilterControl/AdhocFilterPopoverTrigger/index.tsx`
- `superset-frontend/src/explore/components/controls/FixedOrMetricControl/index.tsx`
- `superset-frontend/src/explore/components/controls/MetricControl/AdhocMetricEditPopover/index.tsx`
- `superset-frontend/src/explore/components/controls/NumberControl/index.tsx`
- `superset-frontend/src/explore/components/controls/OptionControls/index.tsx`
- `superset-frontend/src/explore/components/controls/SelectAsyncControl/index.tsx`
- `superset-frontend/src/explore/components/controls/TextControl/index.tsx`
- `superset-frontend/src/explore/components/controls/TimeRangeControl/index.tsx`
- `superset-frontend/src/explore/components/controls/TimeSeriesColumnControl/index.tsx`
- `superset-frontend/src/explore/components/controls/VizTypeControl/index.tsx`
- `superset-frontend/src/explore/components/controls/index.ts`
- `superset-frontend/src/explore/components/useExploreAdditionalActionsMenu/index.tsx`
- `superset-frontend/src/explore/exploreUtils/index.ts`
- `superset-frontend/src/features/databases/DatabaseModal/DatabaseConnectionForm/index.tsx`
- `superset-frontend/src/features/databases/DatabaseModal/index.tsx`
- `superset-frontend/src/features/databases/UploadDataModel/index.tsx`
- `superset-frontend/src/features/datasets/AddDataset/DatasetPanel/index.tsx`
- `superset-frontend/src/features/datasets/AddDataset/EditDataset/index.tsx`
- `superset-frontend/src/features/datasets/AddDataset/Footer/index.tsx`
- `superset-frontend/src/features/datasets/AddDataset/Header/index.tsx`
- `superset-frontend/src/features/datasets/AddDataset/LeftPanel/index.tsx`
- `superset-frontend/src/features/datasets/AddDataset/RightPanel/index.tsx`
- `superset-frontend/src/features/datasets/DatasetLayout/index.tsx`
- `superset-frontend/src/features/datasets/DatasetSelectLabel/index.tsx`
- `superset-frontend/src/features/reports/ReportModal/HeaderReportDropdown/index.tsx`
- `superset-frontend/src/features/reports/ReportModal/index.tsx`
- `superset-frontend/src/filters/components/Range/index.ts`
- `superset-frontend/src/filters/components/Select/index.ts`
- `superset-frontend/src/filters/components/Time/index.ts`
- `superset-frontend/src/filters/components/TimeColumn/index.ts`
- `superset-frontend/src/filters/components/TimeGrain/index.ts`
- `superset-frontend/src/hooks/useBeforeUnload/index.ts`
- `superset-frontend/src/hooks/useConfirmModal/index.tsx`
- `superset-frontend/src/hooks/useUnsavedChangesPrompt/index.ts`
- `superset-frontend/src/logger/actions/index.ts`
- `superset-frontend/src/pages/ActionLog/index.tsx`
- `superset-frontend/src/pages/AlertReportList/index.tsx`
- `superset-frontend/src/pages/AllEntities/index.tsx`
- `superset-frontend/src/pages/AnnotationLayerList/index.tsx`
- `superset-frontend/src/pages/AnnotationList/index.tsx`
- `superset-frontend/src/pages/Chart/index.tsx`
- `superset-frontend/src/pages/ChartCreation/index.tsx`
- `superset-frontend/src/pages/ChartList/index.tsx`
- `superset-frontend/src/pages/CssTemplateList/index.tsx`
- `superset-frontend/src/pages/Dashboard/index.tsx`
- `superset-frontend/src/pages/DashboardList/index.tsx`
- `superset-frontend/src/pages/DatabaseList/index.tsx`
- `superset-frontend/src/pages/DatasetCreation/index.tsx`
- `superset-frontend/src/pages/DatasetList/index.tsx`
- `superset-frontend/src/pages/ExecutionLogList/index.tsx`
- `superset-frontend/src/pages/FileHandler/index.tsx`
- `superset-frontend/src/pages/GroupsList/index.tsx`
- `superset-frontend/src/pages/Home/index.tsx`
- `superset-frontend/src/pages/Login/index.tsx`
- `superset-frontend/src/pages/QueryHistoryList/index.tsx`
- `superset-frontend/src/pages/RedirectWarning/index.tsx`
- `superset-frontend/src/pages/Register/index.tsx`
- `superset-frontend/src/pages/RolesList/index.tsx`
- `superset-frontend/src/pages/RowLevelSecurityList/index.tsx`
- `superset-frontend/src/pages/SavedQueryList/index.tsx`
- `superset-frontend/src/pages/SqlLab/index.tsx`
- `superset-frontend/src/pages/Tags/index.tsx`
- `superset-frontend/src/pages/TaskList/index.tsx`
- `superset-frontend/src/pages/ThemeList/index.tsx`
- `superset-frontend/src/pages/UserInfo/index.tsx`
- `superset-frontend/src/pages/UserRegistrations/index.tsx`
- `superset-frontend/src/pages/UsersList/index.tsx`
- `superset-frontend/src/utils/getChartFormDiffs/index.ts`
- `superset-frontend/src/utils/sanitizeFormData/index.ts`
- `superset-frontend/src/views/App.tsx`
- `superset-frontend/src/views/index.tsx`
- `superset-frontend/src/visualizations/TimeTable/index.ts`
- `superset-websocket/src/index.ts`
- `superset-websocket/utils/client-ws-app/app.js`
- `superset-websocket/utils/client-ws-app/public/javascripts/app.js`
- `superset-websocket/utils/client-ws-app/routes/index.js`
- `superset/app.py`
- `superset/cli/main.py`
- `superset/mcp_service/__main__.py`
- `superset/mcp_service/app.py`
- `superset/mcp_service/index.js`
- `superset/mcp_service/server.py`

## Core modules

_Confidence: `INFERRED` (DEC-015)._

The load-bearing files — highest dependency centrality (PageRank over the symbol graph):

1. `superset-frontend/packages/superset-core/src/translation/TranslatorSingleton.ts` (centrality 0.0225)
2. `superset-frontend/packages/superset-core/src/theme/index.tsx` (centrality 0.0208)
3. `superset-frontend/packages/superset-core/src/translation/Translator.ts` (centrality 0.0194)
4. `superset/utils/core.py` (centrality 0.0130)
5. `superset/migrations/shared/utils.py` (centrality 0.0099)
6. `superset-frontend/src/components/MessageToasts/withToasts.tsx` (centrality 0.0092)
7. `superset/errors.py` (centrality 0.0086)
8. `superset/exceptions.py` (centrality 0.0078)

## Layers

Top-level directories by analyzed-file count:

| Directory | Files |
| --- | --- |
| `superset-frontend` | 2,068 |
| `superset` | 1,106 |
| `docs` | 44 |
| `superset-core` | 21 |
| `scripts` | 14 |
| `superset-websocket` | 8 |
| `superset-embedded-sdk` | 4 |
| `superset-extensions-cli` | 4 |
| `RELEASING` | 3 |
| `docker` | 3 |
| `(repo root)` | 1 |

---

*Generated by forensic-deepdive 0.8.0 on 2026-06-22. Regenerate with `forensic update` — do not hand-edit.*
