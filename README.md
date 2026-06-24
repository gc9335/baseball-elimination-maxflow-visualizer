# 实验六：最大流应用——棒球淘汰问题

本项目使用 Python 独立实现两种最大流算法，并将棒球淘汰问题转换为最大流问题：

- 基准算法：Edmonds–Karp
- 优化算法：Dinic（分层图、阻塞流、当前弧优化）

程序可以输出球队是否被淘汰、淘汰证明集合、最大流值，并能批量测试 Princeton 官方数据和生成算法性能对比图。

## 1. 环境

推荐 Python 3.10 及以上版本。

```powershell
python -m pip install -r requirements.txt
```

核心最大流和棒球淘汰算法只使用 Python 标准库；Matplotlib、Seaborn 用于绘图，pytest 用于自动化测试。

## 2. 项目结构

```text
baseball_elimination/
├── flow_network.py     # 残量网络
├── edmonds_karp.py     # 基准算法
├── dinic.py            # 优化算法
├── baseball.py         # 数据解析、流网络构造、淘汰判定
└── cli.py              # 命令行
data/
├── teams4.txt          # 题目四队样例
├── teams5.txt
└── princeton/          # 23 个官方测试文件
scripts/
├── download_datasets.py
└── benchmark.py
tests/                  # 自动化测试
output/                 # CSV、性能图和批测结果
main.py
实验报告.md
```

## 3. 输入格式

第一行为球队数 `n`，之后每行依次为：

```text
球队名 已胜场数 已负场数 剩余场数 与第1队剩余场数 ... 与第n队剩余场数
```

球队名不能含空格，因此 New York 写作 `New_York`。题目图片中的四队数据已经保存为 `data/teams4.txt`。

## 4. 运行

默认使用 Dinic：

```powershell
python main.py data/teams4.txt
```

指定基准算法：

```powershell
python main.py data/teams4.txt --algorithm edmonds-karp
```

只分析费城队并显示详细数据：

```powershell
python main.py data/teams4.txt --team Philadelphia --details
```

四队样例输出：

```text
Atlanta is not eliminated
Philadelphia is eliminated by the subset R = { Atlanta New_York }
New_York is not eliminated
Montreal is eliminated by the subset R = { Atlanta }
```

## 5. 测试

```powershell
python -m pytest -q
```

重新下载 Princeton 官方数据：

```powershell
python scripts/download_datasets.py
```

官方数据来源：[Princeton Baseball Elimination](https://coursera.cs.princeton.edu/algs4/assignments/baseball/specification.php)。

## 6. 性能实验

```powershell
python scripts/benchmark.py --repeats 5
```

输出：

- `output/benchmark_results.csv`：每次计时的原始结果。
- `output/maxflow_comparison.png`：两种算法的中位耗时对比图。
- `output/test_results.txt`：23 个官方文件的批测摘要。

随机实验使用固定种子，因此可以复现。不同电脑的绝对耗时会变化，但算法结论和整体增长趋势应保持一致。
