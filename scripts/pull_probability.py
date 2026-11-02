#!/usr/bin/env python3
"""
抽卡概率通用计算（纯标准库）。

解析法：单目标抽数分布、期望、分位、预算成功率，以及同池多金的独立卷积。
蒙特卡洛：逐抽模拟，处理带状态的捕获明光、同池多金、大保底等复杂分支。
  - 稳态口径：连续长链，反映捕获明光下的长期平均成本。
  - 条件口径：从用户当前垫抽/保底/捕获计数出发，推算接下来的抽取。
氪金填充：按当期价格表，以单位抽成本从低到高贪心补足缺口。
全收集缺口：长期收支速率平衡，估算每版本与累计缺口。

可作为模块导入，也可命令行运行：
  python pull_probability.py --base 0.006 --soft-start 74 --hard 90 --up-p 0.5 --budget 180
  大保底加 --guarantee；捕获明光加 --cr；同池多金加 --copies 2。
"""
import argparse
import random


# 原神捕获明光：各“连续大保底计数”状态下的翻案触发概率。
# 首尾为官方公示（0.018% 与三连歪后 100%），中间两项为标定到综合 UP 率 55% 的推断值。
CR_PROBS = [0.00018, 0.10, 0.1704, 1.0]


def make_q(base, soft_start, hard, step=0.06):
    """生成单抽出金概率函数。soft_start 抽起每抽递增 step，hard 抽必出。"""
    def q(k):
        if k <= soft_start - 1:
            return base
        return min(1.0, base + step * (k - (soft_start - 1)))
    return q


def dist_to_s(q, hard, pity):
    """从已垫 pity 抽到下一个金的抽数分布：还需 r 抽 -> 概率。"""
    d = {}
    survive = 1.0
    for r in range(1, hard - pity + 1):
        p = q(pity + r)
        d[r] = survive * p
        survive *= (1 - p)
    return d


def conv_dist(d1, d2):
    """两个独立随机变量分布的卷积。"""
    out = {}
    for a, pa in d1.items():
        for b, pb in d2.items():
            out[a + b] = out.get(a + b, 0.0) + pa * pb
    return out


def scale_dist(d, p):
    return {k: v * p for k, v in d.items()}


def merge_dist(*ds):
    out = {}
    for d in ds:
        for k, v in d.items():
            out[k] = out.get(k, 0.0) + v
    return out


def featured_dist(q, hard, pity, up_p, guarantee=False):
    """
    获得当期限定的总抽数分布（标准 50-50，不含捕获明光）。
    guarantee=True 表示当前已是大保底，下一金即 UP。
    """
    first = dist_to_s(q, hard, pity)
    if guarantee:
        return first
    second = dist_to_s(q, hard, 0)
    return merge_dist(
        scale_dist(first, up_p),
        conv_dist(scale_dist(first, 1 - up_p), second),
    )


def multi_copies_dist(q, hard, up_p, copies, pity=0, guarantee=False):
    """
    同池连续拿 copies 个 UP 金的解析分布（标准 50-50，各保底周期独立）。
    第一个金受初始 pity/guarantee 影响，其后均从 0 垫、非保底开始。
    """
    combined = featured_dist(q, hard, pity, up_p, guarantee)
    for _ in range(copies - 1):
        combined = conv_dist(combined, featured_dist(q, hard, 0, up_p, False))
    return combined


def simulate_chain(q, hard, up_p, total, start_pity=0, guarantee=False,
                   cr_probs=None, start_cr=0, rng=None):
    """
    连续抽取 total 个 UP 金，捕获计数在整条链内累积。
    返回每个 UP 金的实际成本列表与总抽数。
    """
    rng = rng or random
    per_gold = []
    cur_pity = start_pity
    guaranteed = guarantee
    cr_count = start_cr
    got = 0
    gold_pulls = 0
    while got < total:
        while True:
            cur_pity += 1
            gold_pulls += 1
            if rng.random() < q(cur_pity):
                break
        if guaranteed:
            is_up = True
            guaranteed = False
        elif rng.random() < up_p:
            is_up = True
            cr_count = 0
        elif cr_probs is not None and rng.random() < cr_probs[cr_count]:
            is_up = True
            cr_count = 0
        else:
            is_up = False
            guaranteed = True
            cur_pity = 0
            cr_count += 1
        if is_up:
            got += 1
            cur_pity = 0
            per_gold.append(gold_pulls)
            gold_pulls = 0
    return per_gold, sum(per_gold)


def _quant(sorted_list, x):
    idx = max(0, int(x * len(sorted_list)) - 1)
    return sorted_list[idx]


def _stats_from_list(vals, budget=None):
    s = sorted(vals)
    stats = {
        "expected": round(sum(s) / len(s), 1),
        "p25": _quant(s, 0.25),
        "p50": _quant(s, 0.50),
        "p75": _quant(s, 0.75),
        "p90": _quant(s, 0.90),
        "p95": _quant(s, 0.95),
        "p99": _quant(s, 0.99),
        "max": s[-1],
    }
    if budget is not None:
        stats["success"] = round(
            sum(1 for v in s if v <= budget) / len(s), 4)
    return stats


def steady_state_stats(q, hard, up_p, cr_probs, budget=None,
                       warmup=300, size=5000, seed=None):
    """稳态下单个 UP 金的成本分布；cr_probs=None 时退化为标准 50-50。"""
    rng = random.Random(seed)
    per_gold, _ = simulate_chain(
        q, hard, up_p, warmup + size, cr_probs=cr_probs, rng=rng)
    return _stats_from_list(per_gold[warmup:], budget)


def monte_carlo(q, hard, up_p, copies=1, pity=0, guarantee=False,
                cr_probs=None, start_cr=0, trials=20000,
                budget=None, seed=None):
    """从当前状态出发，连续拿 copies 个 UP 金的总抽数分布（条件口径）。"""
    rng = random.Random(seed)
    totals = []
    for _ in range(trials):
        _, total = simulate_chain(
            q, hard, up_p, copies, pity, guarantee,
            cr_probs, start_cr, rng)
        totals.append(total)
    return _stats_from_list(totals, budget)


def _normalized(d):
    total = sum(d.values())
    return sorted(d.items()), total


def expected(d):
    items, total = _normalized(d)
    return sum(k * p for k, p in items) / total


def percentile(d, x):
    items, total = _normalized(d)
    target = x * total
    acc = 0.0
    for k, p in items:
        acc += p
        if acc >= target:
            return k
    return items[-1][0]


def summarize(d):
    return {
        "expected": round(expected(d), 1),
        "p25": percentile(d, 0.25),
        "p50": percentile(d, 0.50),
        "p75": percentile(d, 0.75),
        "p90": percentile(d, 0.90),
        "p95": percentile(d, 0.95),
        "p99": percentile(d, 0.99),
        "max": max(d),
    }


def success_rate(d, budget):
    total = sum(d.values())
    return sum(p for k, p in d.items() if k <= budget) / total


def multi_target_success(dist_list, budget):
    """多个独立池目标在总预算内全部拿到的概率（解析卷积）。"""
    combined = dist_list[0]
    for d in dist_list[1:]:
        combined = conv_dist(combined, d)
    return success_rate(combined, budget)


def top_up_plan(gap, packages, instant_only=False):
    """
    按单位抽成本从低到高贪心补足 gap 抽。
    packages: [{"name", "pulls", "price", "instant", "limit"}]
    instant_only=True 时只选即时到账手段（月卡/纪行等分期手段排除）。
    返回所选方案、总花费与仍未补足抽数。价格表当期获取，不固化。
    """
    cands = sorted(packages, key=lambda x: x["price"] / x["pulls"])
    chosen = []
    total = 0.0
    remaining = gap
    for pkg in cands:
        if instant_only and not pkg.get("instant", True):
            continue
        if remaining <= 0:
            break
        times = min(pkg.get("limit", 1), -(-remaining // pkg["pulls"]))
        if times > 0:
            chosen.append({
                "name": pkg["name"],
                "units": times,
                "cost": round(times * pkg["price"], 2),
            })
            total += times * pkg["price"]
            remaining -= times * pkg["pulls"]
    return chosen, round(total, 2), max(0, remaining)


def collection_gap(new_per_patch, expected_pulls, income_per_patch,
                   backlog=0, patches=12):
    """
    全收集模式的长期收支缺口。目标随版本新限定自动生成，不逐时点建账。
    new_per_patch: 每版本平均新限定数
    expected_pulls: 单限定期望抽数（标准 93.4 或含捕获明光 90.3）
    income_per_patch: 每版本资源收入（月卡中值）
    backlog: 开局存量未收集限定数
    返回每版本成本、每版本缺口、n 版本累计缺口与可行性。
    """
    cost_per_patch = new_per_patch * expected_pulls
    gap_per_patch = cost_per_patch - income_per_patch
    cumulative = backlog * expected_pulls + gap_per_patch * patches
    return {
        "cost_per_patch": round(cost_per_patch, 1),
        "gap_per_patch": round(gap_per_patch, 1),
        "cumulative_gap": round(cumulative, 1),
        "feasible": gap_per_patch <= 0 and backlog == 0,
    }


def main():
    ap = argparse.ArgumentParser(description="抽卡概率计算")
    ap.add_argument("--base", type=float, required=True)
    ap.add_argument("--soft-start", type=int, required=True)
    ap.add_argument("--hard", type=int, required=True)
    ap.add_argument("--up-p", type=float, required=True)
    ap.add_argument("--pity", type=int, default=0)
    ap.add_argument("--step", type=float, default=0.06)
    ap.add_argument("--budget", type=int)
    ap.add_argument("--guarantee", action="store_true")
    ap.add_argument("--copies", type=int, default=1, help="同池连续 UP 金数量")
    ap.add_argument("--cr", action="store_true", help="启用捕获明光")
    ap.add_argument("--trials", type=int, default=20000)
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()

    q = make_q(args.base, args.soft_start, args.hard, args.step)
    cr_probs = CR_PROBS if args.cr else None

    if args.cr and args.copies == 1:
        print("捕获明光稳态统计:",
              steady_state_stats(q, args.hard, args.up_p,
                                 cr_probs, args.budget, seed=args.seed))
    elif args.copies > 1:
        print("同池多金条件统计:",
              monte_carlo(q, args.hard, args.up_p, args.copies, args.pity,
                          args.guarantee, cr_probs, 0, args.trials,
                          args.budget, args.seed))
    else:
        d = featured_dist(q, args.hard, args.pity, args.up_p, args.guarantee)
        print("限定目标抽数统计:", summarize(d))
        if args.budget is not None:
            print("预算 %d 抽内成功率: %.2f%%" % (
                args.budget, 100 * success_rate(d, args.budget)))


if __name__ == "__main__":
    main()
