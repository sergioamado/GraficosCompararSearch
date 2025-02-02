import pandas as pd
import matplotlib.pyplot as plt

def create_grouped_problem_charts(df, selected_problems):
    """Cria gráficos de barras horizontais para cada problema selecionado, comparando algoritmos."""

    for problem in selected_problems:
        problem_df = df[df['problem'] == problem]
        
        if len(problem_df) == 0:
            print(f"No data found for problem: {problem}")
            continue

        print(f"Creating charts for problem: {problem}")
        
        metrics = ['nodes', 'goal', 'cost', 'actions']
        fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(15, 10))
        axes = axes.flatten()

        for i, metric in enumerate(metrics):
             
            df_pivot = problem_df.pivot_table(index='search', values=metric, aggfunc='first')
            df_pivot.plot(kind='barh',ax=axes[i],legend=False)
            axes[i].set_title(f'{metric.capitalize()} by Algorithm for {problem}')
            axes[i].set_xlabel(metric.capitalize())
            axes[i].set_ylabel('Algorithm')
            axes[i].tick_params(axis='y', rotation=0)
        plt.tight_layout()
        plt.show()

# Carregar os dados do CSV
df = pd.read_csv("output.csv")

# Listar os problemas disponíveis com índices
available_problems = df['problem'].unique()
print("Available problems:")
for i, problem in enumerate(available_problems):
    print(f"Option {i+1}: {problem}")

# Permitir que o usuário escolha os problemas por número
selected_problems_str = input("Enter the option numbers (separated by commas) of the problems you want to plot: ")
selected_problem_numbers = [int(x.strip()) - 1 for x in selected_problems_str.split(",")]

# Filtra os problemas selecionados, verificando entradas inválidas
selected_problems = [available_problems[i] for i in selected_problem_numbers if 0<=i<len(available_problems)]

# Gerar os gráficos para os problemas selecionados
create_grouped_problem_charts(df, selected_problems)