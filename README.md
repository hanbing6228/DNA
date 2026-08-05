# DNA Personal Genome Intelligence v0.4

**医学推理引擎 + 个人健康档案整合 + 高级专业报告**

## 核心架构

```
VCF File
  ↓
Variant Annotation (ClinVar / SnpEff / HGVS)
  ↓
Medical Reasoning Engine
  ├─ Inheritance Engine (AD/AR/XL, zygosity, penetrance)
  ├─ Evidence Engine (impact + ClinVar + review status)
  ├─ Risk Classifier (5 clinical categories)
  ├─ Actionability Engine (disease severity + interventions)
  ├─ Phenotype Matcher (personal context integration)
  └─ Medication Engine (pharmacogenomics)
  ↓
Personalized Report (HTML + JSON)
```

## 文件结构

```
DNA-v04/
├── app.py                          # 主入口
├── engine/
│   ├── vcf_parser.py              # VCF/GZ 解析
│   ├── ann_parser.py              # SnpEff ANN
│   ├── clinvar_parser.py          # ClinVar 提取
│   ├── inheritance_engine.py      # 遗传模式推理
│   ├── evidence_engine.py         # 证据评分
│   ├── risk_classifier.py         # 临床风险分类
│   ├── actionability_engine.py    # 可操作性评估
│   ├── phenotype_matcher.py       # 个人背景匹配
│   ├── medication_engine.py       # 药物基因组
│   └── report_engine.py           # 高级HTML报告
├── knowledge/
│   ├── inheritance.json           # 基因遗传模式库
│   ├── diseases.json              # 疾病信息库
│   └── drugs.json                 # 药物基因组学库
├── user_profile/
│   └── profile.json               # 个人健康档案
├── static/
│   └── style.css                  # 高级暗色主题CSS
└── reports/                       # 输出目录
```

## 快速开始

```bash
# 1. 分析 VCF
python app.py /path/to/clinical_ready.vcf.gz

# 2. 带个人档案
python app.py clinical_ready.vcf.gz --profile user_profile/profile.json

# 3. 测试模式（1000条）
python app.py clinical_ready.vcf.gz --max-variants 1000

# 4. 查看报告
open reports/report.html
```

## 报告分类

| 类别 | 图标 | 含义 | 示例 |
|---|---|---|---|
| 需要临床行动 | 🔴 | AD致病+可能发病 | PRSS1 杂合致病 |
| 药物基因组学 | 💊 | 影响药物代谢 | DPYD → 5-FU毒性 |
| 疾病风险 | 🟠 | 风险因素/复杂遗传 | APOE → 阿尔茨海默 |
| 携带者状态 | 🟡 | AR杂合，不发病 | NAGLU 携带者 |

## 个人档案字段

```json
{
  "basic": { "age": 38, "sex": "female", "ancestry": "East Asian" },
  "conditions": ["anxiety", "ADHD"],
  "medications": ["bupropion"],
  "family_history": [{"condition": "pancreatitis", "relation": "father"}],
  "lifestyle": { "smoking": false, "alcohol": "none", "exercise": "moderate" },
  "lab_results": { "LDL": {"value": 140, "unit": "mg/dL"} }
}
```

## 医学推理示例

### PRSS1 c.47C>T (杂合)

**Before (v0.2):**
```
Pathogenic | HIGH | Hereditary pancreatitis
```

**After (v0.4):**
```
🔴 需要临床行动
PRSS1 p.Ala16Val
遗传模式: 常染色体显性
基因型: 杂合
外显率: ~80%

医学解读: 与遗传性胰腺炎相关。携带一个致病等位基因
         即可发病，但需结合临床表现。

建议行动:
  ✓ 避免饮酒
  ✓ 避免吸烟
  ✓ 监测腹痛症状
  ✓ 遗传咨询

👤 基于您的个人档案:
  家族史: 父亲有胰腺炎
  风险评估: 家族史中有相关记录，结合基因结果，建议加强监测
```

### NAGLU (杂合)

**Before (v0.2):**
```
Pathogenic | HIGH | MPS III B
```

**After (v0.4):**
```
🟡 携带者状态
NAGLU p.Asp559Asn
遗传模式: 常染色体隐性
基因型: 杂合

医学解读: 杂合携带者。常染色体隐性遗传，单个致病等位
         基因通常不发病。

建议行动:
  ✓ 生育前建议伴侣进行携带者筛查
  ✓ 保持健康生活方式
  ✓ 定期体检
```

## 技术特性

- ✅ **零外部依赖** — 纯 Python 标准库
- ✅ **高级暗色主题** — 医疗级专业 UI
- ✅ **响应式设计** — 支持手机/平板/桌面
- ✅ **中文原生** — 全部输出中文
- ✅ **模块化引擎** — 每层可独立扩展

## 后续开发

- [ ] Apple Health XML 解析
- [ ] 体检报告 OCR
- [ ] Polygenic Risk Score
- [ ] AI 解释层 (LLM)
- [ ] 知识库自动更新
- [ ] PDF 导出

## 免责声明

仅供教育和研究参考，不能替代专业医疗建议。
