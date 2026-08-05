class PhenotypeMatcher:
    """表型匹配引擎：基因 + 个人背景 = 个性化风险评估"""

    @staticmethod
    def match(variant_data, user_profile):
        if not user_profile:
            return None

        gene = variant_data.get('gene_name', '')
        disease = variant_data.get('disease', '')
        category = variant_data.get('category', '')

        context = {
            'relevant_conditions': [],
            'relevant_medications': [],
            'relevant_family': [],
            'relevant_labs': [],
            'lifestyle_factors': [],
            'personalized_risk': '',
            'personalized_advice': [],
            'risk_modifier': 0,
        }

        # 药物基因组学
        if category == 'pharmacogenomics':
            for med in user_profile.get('medications', []):
                context['relevant_medications'].append(med)
            if context['relevant_medications']:
                context['personalized_risk'] = '您当前正在服用药物，此基因结果可能与用药相关。'
                context['personalized_advice'].append('建议将此基因报告分享给开药医生。')
                context['risk_modifier'] = 2
            else:
                context['personalized_risk'] = '您目前未服用相关药物，此结果供未来用药参考。'

        # 疾病风险：家族史
        if category in ('clinical_action', 'disease_risk'):
            for fh in user_profile.get('family_history', []):
                fh_condition = fh.get('condition', '').lower()
                if fh_condition in disease.lower() or disease.lower() in fh_condition:
                    context['relevant_family'].append(fh)

            if context['relevant_family']:
                relations = '、'.join([f"{f['relation']}有{f['condition']}" for f in context['relevant_family']])
                context['personalized_risk'] = f'您的家族史中有相关记录（{relations}），结合基因结果，建议加强监测。'
                context['personalized_advice'].append('建议与医生讨论早期筛查方案。')
                context['risk_modifier'] = 3
            else:
                context['personalized_risk'] = f'无相关家族史，但基因结果显示风险。建议定期体检。'

        # 生活方式因素
        lifestyle = user_profile.get('lifestyle', {})
        if gene == 'PRSS1':
            if lifestyle.get('alcohol') in ('heavy', 'moderate'):
                context['lifestyle_factors'].append('饮酒可能增加胰腺炎风险')
                context['personalized_advice'].append('建议减少或避免饮酒。')
                context['risk_modifier'] += 1
            if lifestyle.get('smoking'):
                context['lifestyle_factors'].append('吸烟可能增加胰腺炎风险')
                context['personalized_advice'].append('强烈建议戒烟。')
                context['risk_modifier'] += 1

        if gene in ('BRCA1', 'BRCA2') and lifestyle.get('smoking'):
            context['lifestyle_factors'].append('吸烟可能进一步增加癌症风险')
            context['personalized_advice'].append('强烈建议戒烟。')
            context['risk_modifier'] += 1

        # 年龄相关
        age = user_profile.get('basic', {}).get('age')
        if age and gene in ('APOE',):
            if age > 50:
                context['personalized_advice'].append('年龄超过50岁，建议关注认知功能变化。')

        # 实验室指标
        labs = user_profile.get('lab_results', {})
        if gene in ('LDLR', 'APOB', 'PCSK9'):
            ldl = labs.get('LDL', {}).get('value')
            if ldl and ldl > 130:
                context['relevant_labs'].append(f'LDL {ldl} mg/dL（偏高）')
                context['personalized_advice'].append('LDL偏高 + 基因变异，建议积极控制血脂。')
                context['risk_modifier'] += 1

        return context if (context['personalized_risk'] or context['personalized_advice']) else None
