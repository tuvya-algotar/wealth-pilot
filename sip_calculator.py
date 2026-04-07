    def calculate_sip_corpus(monthly_sip, annual_return_pct, years):
        """Standard SIP future value formula"""
        r = annual_return_pct / 100 / 12
        n = years * 12
        if r == 0:
            return monthly_sip * n
        fv = monthly_sip * (((1 + r) ** n - 1) / r) * (1 + r)
        return round(fv)


    def calculate_fire_plan(profile):
        """
        profile: age, monthly_income, monthly_expenses,
                current_investments, risk_appetite (conservative/balanced/aggressive)
        """
        age = profile['age']
        income = profile['monthly_income']
        expenses = profile['monthly_expenses']
        current_inv = profile.get('current_investments', 0)
        risk = profile.get('risk_appetite', 'balanced')

        returns = {'conservative': 9, 'balanced': 11, 'aggressive': 13}
        annual_return = returns[risk]

        # FIRE corpus needed: 25x annual expenses (4% withdrawal rule)
        annual_expenses = expenses * 12
        fire_corpus = annual_expenses * 25

        # How much can they invest monthly?
        investable = income - expenses
        recommended_sip = round(investable * 0.7)  # invest 70% of surplus

        # Find FIRE year
        for years in range(1, 40):
            corpus = current_inv * ((1 + annual_return/100) ** years)
            corpus += calculate_sip_corpus(recommended_sip, annual_return, years)
            if corpus >= fire_corpus:
                return {
                    'fire_age': age + years,
                    'years_to_fire': years,
                    'fire_corpus_needed': fire_corpus,
                    'projected_corpus': round(corpus),
                    'recommended_sip': recommended_sip,
                    'annual_return_assumed': annual_return,
                    'monthly_passive_income': round(fire_corpus * 0.04 / 12)
                }

        return {'error': 'FIRE not achievable in 40 years at current savings rate'}