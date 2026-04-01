# Backend Scripts - 使用指南

本目录包含后端管理和维护脚本。

## 📋 脚本列表

### check_big_expense_consistency.py
**大额开销结余池数据一致性检查工具**

#### 功能说明
- 验证所有家庭的结余池计算是否正确
- 检测数据不一致和透支情况
- 生成详细的检查报告

#### 使用方法

```bash
# 基本使用 - 检查所有家庭
python scripts/check_big_expense_consistency.py

# 查看帮助
python scripts/check_big_expense_consistency.py --help
```

#### 输出说明

**正常输出**:
```
[1/3] 检查家庭: 张家 (ID: 1)
  ✓ 累计预留: 10,000.00
  ✓ 累计支出: 3,500.00
  ✓ 实际结余: 6,500.00

✅ 所有家庭数据一致性检查通过!
```

**异常输出**:
```
[2/3] 检查家庭: 李家 (ID: 2)
  ✓ 累计预留: 5,000.00
  ✓ 累计支出: 6,000.00
  ✓ 实际结余: -1,000.00
  ⚠️  警告: 结余池透支 1,000.00

异常详情:
  - 李家 (ID: 2)
    结余: -1,000.00
    原因: 透支
```

#### 退出码
- `0`: 所有检查通过
- `1`: 发现数据异常

#### 集成到CI/CD

在 `.github/workflows/test.yml` 中添加：

```yaml
- name: Check Big Expense Consistency
  run: |
    cd backend
    python scripts/check_big_expense_consistency.py
```

#### 定期检查（Cron）

```bash
# 每天凌晨2点运行
crontab -e

# 添加以下行
0 2 * * * cd /path/to/family-hub/backend && python scripts/check_big_expense_consistency.py
```

#### 监控告警集成

```bash
# 运行并在失败时发送告警
python scripts/check_big_expense_consistency.py || \
  curl -X POST https://hooks.slack.com/... \
  -d '{"text":"大额开销数据一致性检查失败!"}'
```

---

## 🔧 开发新脚本

### 脚本模板

```python
#!/usr/bin/env python3
"""
脚本说明

用途：...
运行：python scripts/your_script.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, Base


async def main():
    """主函数"""
    async with AsyncSession(engine) as session:
        # Your code here
        pass


if __name__ == "__main__":
    asyncio.run(main())
```

### 最佳实践

1. **添加清晰的文档字符串** - 说明脚本用途和使用方法
2. **使用异步数据库会话** - 遵循应用统一的异步模式
3. **提供退出码** - 0表示成功，非0表示失败
4. **添加进度提示** - 对于长时间运行的脚本
5. **支持命令行参数** - 使用 `argparse` 提供灵活性
6. **错误处理** - 捕获并友好显示错误信息

---

## 📚 相关文档

- [大额开销功能优化说明](../../docs/BIG-EXPENSE-IMPROVEMENTS.md)
- [Admin API文档](../app/routers/admin.py)

---

### backfill_expense_diamond_spends.py
**历史记账“消费钻石”回填脚本（用于等级进度）**

#### 功能说明
- 将历史支出记录转换为“消费钻石”并写入 `expense_diamond_spends`
- 支持分摊：有 splits 则按分摊成员分配，不算到付款人
- 支持汇率：先换算到 CNY，再按 `钻石 = round(CNY * 10)`

#### 使用方法

```bash
# 回填全部家庭（推荐先 dry-run 看数量/速度）
python scripts/backfill_expense_diamond_spends.py --dry-run

# 真正回填（第一次建议 reset 全量重建）
python scripts/backfill_expense_diamond_spends.py --reset-all

# 仅回填某个家庭
python scripts/backfill_expense_diamond_spends.py --family-id 1 --reset-all

# 调整批大小（数据量很大时可以调大）
python scripts/backfill_expense_diamond_spends.py --batch-size 1000 --reset-all
```
