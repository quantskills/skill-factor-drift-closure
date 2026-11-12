# 数据契约

最小输入由四部分组成：

1. `panel`：`date`、`symbol`、冻结预测或因子列、成熟标签列；
2. `alerts`：`date`、`alert_type`、`status`，其中只有明确的 `warning` 进入动作；
3. `config`：校准区间、评估区间、成熟度、持有期、训练窗口、purge/embargo、成本和动作参数；
4. `provenance`：数据来源、生成时间、版本、SHA256 和可见性边界。

要求：按 `(date, symbol)` 唯一；标签成熟日期必须晚于持有期；评估期标签不能参与阈值选择；缺失、重复和右删失必须显式记录。
