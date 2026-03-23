# Forecasting Workflow Explanation

# 预测模块工作思路说明

## 1. Overall Goal / 整体目标

The goal of forecasting work was to make the system able to answer three practical questions:
预测这部分工作的目标，是让系统能够回答三个实际问题：

1. How much demand will each store face in the next few days?  
   未来几天每家门店大概会有多少需求？
2. Will the store or warehouse have enough inventory to support that demand?  
   门店或仓库的库存够不够支撑这些需求？
3. Can the order still meet the SLA target, and if not, where is the risk?  
   订单还能不能按 SLA 目标完成，如果不能，风险在哪里？

So the work was not just “building a model”.
所以这部分工作并不只是“训练一个模型”。

It had to form a complete chain:
它需要形成一条完整链路：

historical data -> forecasting model -> prediction result -> API output -> frontend or other modules can use it  
历史数据 -> 预测模型 -> 预测结果 -> API 输出 -> 前端或其他模块可直接使用

---

## 2. Step 1: Clarify What Needs to Be Predicted / 第一步：先明确到底要预测什么

Before writing code, the first thing was to define the target clearly.
写代码之前，第一步先明确“到底要预测什么”。

There are two different prediction tasks in this project:
这个项目里其实有两类不同的预测任务：

### 2.1 Demand Forecasting / 需求预测

This answers:
它回答的是：

- how many products may be needed in each store on each day  
  每个门店每天可能会需要多少商品

This is the base for later inventory and routing decisions.
这是后面做库存和调度决策的基础。

### 2.2 SLA Forecasting / SLA 预测

This answers:
它回答的是：

- whether the store can finish orders on time  
  门店能不能按时完成订单
- what the predicted SLA achievement rate is  
  预测 SLA 达成率是多少
- what risk factors may cause delay  
  哪些风险因素可能导致延迟

So the work was divided into two modules:
因此这部分工作自然分成两个模块：

1. demand forecasting module  
   需求预测模块
2. SLA forecasting module  
   SLA 预测模块

---

## 3. Step 2: Prepare the Input Data / 第二步：整理预测输入数据

A forecasting model cannot work without clean input data.
预测模型如果没有整理好的输入数据，是无法工作的。

So the next step was to decide what data should be used.
所以第二步就是确定模型应该吃什么数据。

The input data mainly came from these parts:
输入数据主要来自以下几部分：

1. Historical order data  
   历史订单数据
2. Store-level daily aggregated demand  
   门店维度的每日需求汇总
3. External features  
   外部特征

External features include:
外部特征包括：

- weather  
  天气
- holiday signals  
  节假日标记
- traffic-related patterns  
  交通相关模式
- weekend / month-end / seasonal effects  
  周末、月末、季节性影响

In simple words:
通俗地说就是：

the model should not only know “what happened before”,  
模型不能只知道“以前卖了多少”，

it should also know “what special conditions may affect future demand or SLA”.
还要知道“未来有没有特殊情况会影响需求或 SLA”。

That is why the code contains feature engineering logic.
这也是为什么代码里会出现特征工程逻辑。

Related files:
对应文件：

- [src/modules/forecasting/prophet_forecaster.py](D:/Download/Pycharm/PycharmProjects/src/modules/forecasting/prophet_forecaster.py)
- [src/modules/forecasting/sla_predictor.py](D:/Download/Pycharm/PycharmProjects/src/modules/forecasting/sla_predictor.py)
- [src/api/services/forecasting_service.py](D:/Download/Pycharm/PycharmProjects/src/api/services/forecasting_service.py)

---

## 4. Step 3: Build the Demand Forecasting Module / 第三步：建立需求预测模块

After the target and data were clear, the next step was to build the demand forecasting module.
在目标和数据都明确以后，下一步就是建立需求预测模块。

### 4.1 Why Prophet / 为什么选 Prophet

Demand data is time-series data.
需求数据本质上是时间序列数据。

That means:
也就是说：

- yesterday affects today  
  昨天会影响今天
- weekdays and weekends behave differently  
  工作日和周末表现不同
- holidays may create demand spikes  
  节假日可能会造成需求上升
- some stores have stable patterns over time  
  一些门店会有长期稳定模式

Prophet is suitable for this kind of trend + seasonality forecasting.
Prophet 很适合处理这种“趋势 + 季节性”的预测问题。

So the implementation used `ProphetForecaster` as the main demand forecasting engine.
因此这里使用 `ProphetForecaster` 作为主需求预测引擎。

### 4.2 What the module does / 这个模块具体做了什么

The module does the following:
这个模块主要做了以下事情：

1. Read training data  
   读取训练数据
2. Aggregate order quantity by store and date  
   按门店和日期聚合订单量
3. Add external features  
   添加外部特征
4. Train one model for each store  
   为每个门店训练一个模型
5. Predict future demand  
   预测未来需求
6. Output confidence intervals  
   输出置信区间

### 4.3 Why confidence intervals are important / 为什么要输出置信区间

Forecasting is never 100% exact.
预测永远不可能 100% 精准。

So the system should not only say:
所以系统不能只说：

- predicted demand is 100  
  预测需求是 100

It should also say:
它还应该说：

- pessimistic case may be 80  
  偏保守情况下可能是 80
- normal case is 100  
  正常情况下是 100
- optimistic / high-demand case may be 120  
  偏高需求情况下可能是 120

That is why the output includes:
所以输出中加入了：

- `P10`
- `P50`
- `P90`

This is very useful later for inventory planning and robust routing.
这对后面的库存规划和鲁棒调度都很有帮助。

---

## 5. Step 4: Make the Demand Module Reliable / 第四步：让需求预测模块更可靠

In real development, one common problem is:
在真实开发里，一个很常见的问题是：

the environment may not always have every package installed.
环境里不一定总是装好了所有依赖。

For example:
比如：

- `prophet` may be missing  
  可能没有安装 `prophet`

If the code crashes immediately because Prophet is missing, then the whole API cannot be used.
如果代码一旦缺少 Prophet 就直接崩掉，那么整个 API 就没法用。

So an important improvement was:
所以这里有一个很重要的工程化处理：

build a fallback forecasting model.
做了一个回退预测模型。

That means:
也就是说：

- if Prophet exists, use Prophet  
  如果 Prophet 存在，就用 Prophet
- if Prophet does not exist, use an internal statistical fallback model  
  如果 Prophet 不存在，就自动使用内置统计回退模型

This makes the forecasting function much more stable.
这样就让需求预测功能稳定了很多。

This is not mainly about model accuracy.
这一步主要不是提升算法精度。

It is about engineering robustness.
而是提升工程鲁棒性。

---

## 6. Step 5: Build the SLA Forecasting Module / 第五步：建立 SLA 预测模块

After demand forecasting, the next question is:
做完需求预测以后，接下来要解决的问题是：

even if we know demand, can we still fulfill orders on time?
即使知道了需求，我们还能不能按时履约？

This is where the SLA forecasting module comes in.
这就是 SLA 预测模块要解决的问题。

### 6.1 What SLA forecasting means / SLA 预测是什么意思

The system tries to estimate:
系统要估算的是：

- what SLA achievement rate a store may have in the near future  
  某个门店未来一段时间的 SLA 达成率大概是多少
- whether the rate is likely to drop  
  这个达成率会不会下降
- which factors are contributing to risk  
  哪些因素在造成风险

### 6.2 What factors affect SLA / 哪些因素会影响 SLA

The code considers factors such as:
代码中考虑了这些因素：

- demand pressure  
  需求压力
- weather risk  
  天气风险
- traffic risk  
  交通风险
- capacity risk  
  容量风险
- holiday / weekend / time-related effects  
  节假日、周末、时间相关影响
- historical store performance  
  门店历史表现
- supply chain uncertainty  
  供应链不确定性

In plain words:
用通俗的话说：

if a store is already busy,  
如果一个门店本来就很忙，

and tomorrow is a weekend,  
明天又是周末，

and traffic may be worse,  
交通还更堵，

then the chance of late fulfillment becomes higher.
那它发生延迟履约的概率就会更高。

### 6.3 What the module outputs / 模块输出什么

The SLA module outputs:
SLA 模块最终会输出：

- predicted SLA rate  
  预测 SLA 达成率
- confidence interval  
  置信区间
- risk factors  
  风险因子
- improvement recommendations  
  改进建议

So the result is not just a number.
所以它给出的结果不只是一个数字。

It also explains why the risk happens and what should be done.
它还会解释为什么有风险，以及应该怎么处理。

---

## 7. Step 6: Add Risk Alerts / 第六步：把预测结果变成预警

A prediction is useful, but an alert is more practical.
预测结果本身有用，但真正更实用的是“预警”。

So the next step was:
所以下一步就是：

convert SLA prediction into alert information.
把 SLA 预测结果转成预警信息。

The logic is simple:
逻辑其实很直观：

1. predict future SLA  
   先预测未来 SLA
2. compare it with a threshold  
   再和阈值比较
3. if the result is too low, raise an alert  
   如果太低，就触发预警
4. classify severity  
   给预警分级
5. show risk factors and suggested actions  
   同时附上风险因子和建议动作

This helps the business side act before the SLA is actually breached.
这样业务侧就可以在 SLA 真正失败之前，提前处理问题。

---

## 8. Step 7: Extend to Inventory ATP / 第七步：扩展到库存 ATP

Demand forecasting alone is still not enough.
光有需求预测其实还不够。

Because the business also needs to know:
因为业务还需要知道：

- if future demand rises, do we have enough stock?  
  如果未来需求上升，库存够不够？
- which SKU may become shortage?  
  哪些 SKU 可能缺货？
- which SKU may become overstock?  
  哪些 SKU 可能积压？

So the next step was to build ATP and inventory outlook logic.
因此接下来就补了 ATP 和库存展望逻辑。

The basic idea is:
基本思路是：

1. use demand forecast as future committed demand  
   把需求预测结果当成未来承诺需求
2. combine it with current stock  
   再结合当前库存
3. add expected arrivals  
   加上预计到货
4. compute projected available inventory  
   计算预测可用库存
5. classify the inventory status  
   判断库存状态

So the output can tell whether an item is:
这样输出就能告诉系统某个商品是：

- normal  
  正常
- shortage  
  缺货
- overstock  
  过量

This is the bridge from forecasting to inventory decision support.
这是从“预测”走向“库存决策支持”的关键一步。

---

## 9. Step 8: Move Logic out of API Routers / 第八步：把核心逻辑从路由里抽出来

At first, many API routes were using mock or temporary logic.
一开始很多 API 路由里还是 mock 或临时拼装逻辑。

That is common during early development, but it is not ideal in the long run.
这在开发早期很常见，但长期来看并不理想。

Why?
为什么？

Because if forecasting logic is directly mixed into API routes:
因为如果把预测逻辑直接混在 API 路由里：

- the route becomes too long  
  路由会越来越长
- the code becomes hard to test  
  代码会变得难测
- future reuse becomes difficult  
  后续复用会变困难

So an important step was:
所以这里做了一个很关键的动作：

create a separate forecasting service layer.
新增独立的预测服务层。

That service layer does the real work:
这个服务层负责真正的业务逻辑：

- preparing training data  
  准备训练数据
- training models  
  训练模型
- caching model state  
  缓存模型状态
- generating forecasts  
  生成预测结果
- generating inventory outlook  
  生成库存展望
- generating SLA alerts  
  生成 SLA 预警

Then API routes only do:
这样 API 路由就只需要做：

- receive request parameters  
  接收请求参数
- call the forecasting service  
  调用预测服务
- return formatted response  
  返回格式化结果

This is a much cleaner structure.
这种结构会清晰很多。

---

## 10. Step 9: Connect Forecasting to API Endpoints / 第九步：把预测能力正式接进 API

After the service layer was ready, the next step was API integration.
在服务层准备好之后，下一步就是把预测能力正式接进 API。

The following routes were connected:
接入的接口主要包括：

### 10.1 Forecast APIs / 预测接口

- `GET /forecast/demand`  
  获取需求预测结果
- `GET /forecast/demand/trend`  
  获取需求趋势结果
- `GET /forecast/inventory`  
  获取 ATP / 库存展望结果
- `GET /forecast/model-info`  
  获取预测模型信息

### 10.2 SLA APIs / SLA 接口

- `GET /sla/pickup-promise`  
  获取取货承诺时间
- `GET /sla/alerts`  
  获取 SLA 预警
- `GET /sla/bottleneck`  
  获取瓶颈分析
- `GET /sla/statistics`  
  获取 SLA 统计结果

This means the forecasting work is no longer isolated algorithm code.
这意味着预测部分不再只是孤立的算法代码。

It has been turned into backend capability that other parts of the system can call.
它已经变成后端系统里可被其他部分直接调用的能力。

---

## 11. Step 10: Make the Code Testable and Stable / 第十步：让代码可测试、可验证、可稳定运行

A feature is not truly finished if it only “looks complete”.
一个功能如果只是“看起来写完了”，其实还不算真正完成。

It should also:
它还应该：

- compile  
  能编译
- run  
  能运行
- survive missing dependencies when possible  
  在部分依赖缺失时还能退化运行
- pass tests  
  能通过测试

So the last part of the work was stabilization.
因此最后一步就是“收口和稳定化”。

This included:
这一步主要包括：

1. adding fallback logic when `prophet` is missing  
   在 `prophet` 缺失时增加回退逻辑
2. adding fallback logic when `scikit-learn` is missing  
   在 `scikit-learn` 缺失时增加回退逻辑
3. fixing confidence interval behavior  
   修复置信区间行为
4. fixing SLA value clipping into valid range  
   修复 SLA 数值范围裁剪问题
5. fixing model persistence behavior  
   修复模型持久化问题
6. running forecasting-related test suites  
   运行预测相关测试

Final validation result:
最终验证结果：

```text
32 passed in 18.86s
```

This shows the forecasting line is not only written, but also verified.
这说明预测这条线不只是“写出来了”，而且已经做了验证。

---

## 12. Final Summary / 最终总结

This work can be understood as a complete workflow from “predicting the future” to “making the prediction usable by the system”.
这部分工作，可以理解为一条从“预测未来”到“让系统真正用上预测结果”的完整链路。

The step-by-step logic is:
一步一步的整体思路可以概括为：

1. define the prediction targets  
   先明确预测目标
2. prepare historical and external feature data  
   整理历史数据和外部特征
3. build the demand forecasting module  
   建立需求预测模块
4. output confidence intervals  
   输出预测置信区间
5. build the SLA forecasting module  
   建立 SLA 预测模块
6. identify risks and generate alerts  
   识别风险并生成预警
7. extend forecasting results into inventory ATP logic  
   把预测结果扩展到库存 ATP
8. move logic into a dedicated service layer  
   把逻辑抽到独立服务层
9. connect everything to API endpoints  
   把能力正式接到 API
10. validate through tests and engineering stabilization  
    通过测试和工程化手段完成稳定化

In simple words:
用最通俗的话说：

first predict how much demand there will be,  
先预测未来会有多少需求，

then estimate whether stores can still serve on time,  
再判断门店还能不能按时履约，

then estimate whether inventory is enough,  
再看库存够不够，

and finally expose all of that through APIs so the system can really use it.
最后把这些结果通过 API 暴露出来，让整个系统真正用起来。

---

## 13. Related Files / 相关文件

- [src/modules/forecasting/prophet_forecaster.py](D:/Download/Pycharm/PycharmProjects/src/modules/forecasting/prophet_forecaster.py)
- [src/modules/forecasting/sla_predictor.py](D:/Download/Pycharm/PycharmProjects/src/modules/forecasting/sla_predictor.py)
- [src/api/services/forecasting_service.py](D:/Download/Pycharm/PycharmProjects/src/api/services/forecasting_service.py)
- [src/api/routers/forecast.py](D:/Download/Pycharm/PycharmProjects/src/api/routers/forecast.py)
- [src/api/routers/sla.py](D:/Download/Pycharm/PycharmProjects/src/api/routers/sla.py)
- [docs/Forecasting_Completion.md](D:/Download/Pycharm/PycharmProjects/docs/Forecasting_Completion.md)
