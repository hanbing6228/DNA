# DNA Personal Genome Intelligence v2.0

## 架构升级

从 v0.4 的 JSON 文件驱动 → **SQLite 知识图谱 + 规则推理引擎**

```
VCF
  ↓
ClinVar Knowledge Graph (SQLite)
  ↓
Knowledge Service (统一查询接口)
  ↓
Reasoning Engine (继承/证据/风险/行动规则)
  ↓
Personalized Report
```

## 快速开始

### 1. 导入 ClinVar 知识库

```bash
python3 pipeline/import_clinvar.py data/clinical_clinvar_full.vcf.gz
```

### 2. 启动 Web 服务

```bash
bash launch.sh
# 或
python3 web_api_v2.py
```

### 3. 访问

打开浏览器：**http://localhost:5000**

## 核心改进

| v0.4 | v2.0 |
|------|------|
| 手写 JSON 知识库 | ClinVar 自动导入 SQLite |
| 硬编码疾病描述 | 数据库关联 + 推理生成 |
| ANNParser 依赖 SnpEff | 直接解析 ClinVar 原生格式 |
| 评分逻辑简单 | 多维度规则引擎 |
| 无个人上下文 | Phenotype 匹配 + 家族史关联 |
| 结果经常为 0 | 只要 ClinVar 有记录就能匹配 |
