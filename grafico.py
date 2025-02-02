import pandas as pd
import matplotlib.pyplot as plt

def create_grouped_problem_charts(df):
    """Cria gráficos de barras para cada problema, comparando algoritmos."""

    problems = df['problem'].unique()

    for problem in problems:
        problem_df = df[df['problem'] == problem]
        
        if len(problem_df) == 0:
            continue

        print(f"Creating charts for problem: {problem}")
        
        metrics = ['nodes', 'goal', 'cost', 'actions']
        fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(15, 10))
        axes = axes.flatten()

        for i, metric in enumerate(metrics):
             
            df_pivot = problem_df.pivot_table(index='search', values=metric, aggfunc='first')
            df_pivot.plot(kind='bar',ax=axes[i],legend=False)
            axes[i].set_title(f'{metric.capitalize()} by Algorithm for {problem}')
            axes[i].set_ylabel(metric.capitalize())
            axes[i].set_xlabel('Algorithm')
            axes[i].tick_params(axis='x', rotation=45)
        plt.tight_layout()
        plt.show()


# Carregar os dados do CSV
df = pd.read_csv("output.csv")

# Gerar os gráficos
create_grouped_problem_charts(df)