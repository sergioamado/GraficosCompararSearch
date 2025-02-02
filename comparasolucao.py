import pandas as pd
import matplotlib.pyplot as plt
import re
from io import StringIO


data = """
astar_search:
      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)
    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)
      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)
      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)
        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')
       15 nodes |        6 goal |  418 cost |       9 actions | RouteProblem('A', 'B')
       34 nodes |       15 goal |  910 cost |      23 actions | RouteProblem('N', 'L')
       33 nodes |       14 goal |  805 cost |      21 actions | RouteProblem('E', 'T')
       20 nodes |        9 goal |  445 cost |      13 actions | RouteProblem('O', 'M')
       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),
   18,151 nodes |    2,096 goal | 2706 cost |   2,200 actions | TOTAL

uniform_cost_search:
      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)
    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)
      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)
      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)
        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')
       30 nodes |       13 goal |  418 cost |      16 actions | RouteProblem('A', 'B')
       42 nodes |       19 goal |  910 cost |      27 actions | RouteProblem('N', 'L')
       44 nodes |       20 goal |  805 cost |      27 actions | RouteProblem('E', 'T')
       30 nodes |       12 goal |  445 cost |      16 actions | RouteProblem('O', 'M')
      124 nodes |       46 goal |    5 cost |      50 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),
   18,304 nodes |    2,156 goal | 2706 cost |   2,260 actions | TOTAL

breadth_first_search:
      596 nodes |      597 goal |    4 cost |      73 actions | PourProblem((1, 1, 1), 13)
      596 nodes |      597 goal |   15 cost |      73 actions | GreenPourProblem((1, 1, 1), 13)
    2,618 nodes |    2,619 goal |    9 cost |     302 actions | PourProblem((0, 0, 0), 21)
    2,618 nodes |    2,619 goal |   32 cost |     302 actions | GreenPourProblem((0, 0, 0), 21)
      120 nodes |      121 goal |   14 cost |      42 actions | PourProblem((0, 0), 8)
      120 nodes |      121 goal |   36 cost |      42 actions | GreenPourProblem((0, 0), 8)
    2,618 nodes |    2,619 goal |    9 cost |     302 actions | PourProblem((0, 0, 0), 21)
    2,618 nodes |    2,619 goal |   32 cost |     302 actions | GreenPourProblem((0, 0, 0), 21)
        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')
       18 nodes |       19 goal |  450 cost |      10 actions | RouteProblem('A', 'B')
       42 nodes |       43 goal | 1085 cost |      27 actions | RouteProblem('N', 'L')
       36 nodes |       37 goal |  837 cost |      22 actions | RouteProblem('E', 'T')
       30 nodes |       31 goal |  445 cost |      16 actions | RouteProblem('O', 'M')
       81 nodes |       82 goal |    5 cost |      35 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),
   12,111 nodes |   12,125 goal | 2973 cost |   1,548 actions | TOTAL

breadth_first_bfs:
      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)
    1,062 nodes |      124 goal |   15 cost |     127 actions | GreenPourProblem((1, 1, 1), 13)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    3,757 nodes |      420 goal |   24 cost |     428 actions | GreenPourProblem((0, 0, 0), 21)
      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)
      124 nodes |       30 goal |   36 cost |      43 actions | GreenPourProblem((0, 0), 8)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    3,757 nodes |      420 goal |   24 cost |     428 actions | GreenPourProblem((0, 0, 0), 21)
        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')
       28 nodes |       12 goal |  450 cost |      14 actions | RouteProblem('A', 'B')
       55 nodes |       24 goal |  910 cost |      32 actions | RouteProblem('N', 'L')
       51 nodes |       22 goal |  837 cost |      28 actions | RouteProblem('E', 'T')
       40 nodes |       16 goal |  445 cost |      20 actions | RouteProblem('O', 'M')
      124 nodes |       46 goal |    5 cost |      50 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),
   17,068 nodes |    2,032 goal | 2782 cost |   2,119 actions | TOTAL

iterative_deepening_search:
    6,133 nodes |    6,118 goal |    4 cost |     822 actions | PourProblem((1, 1, 1), 13)
    6,133 nodes |    6,118 goal |   15 cost |     822 actions | GreenPourProblem((1, 1, 1), 13)
  288,706 nodes |  288,675 goal |    9 cost |  36,962 actions | PourProblem((0, 0, 0), 21)
  288,706 nodes |  288,675 goal |   62 cost |  36,962 actions | GreenPourProblem((0, 0, 0), 21)
    3,840 nodes |    3,824 goal |   14 cost |     949 actions | PourProblem((0, 0), 8)
    3,840 nodes |    3,824 goal |   36 cost |     949 actions | GreenPourProblem((0, 0), 8)
  288,706 nodes |  288,675 goal |    9 cost |  36,962 actions | PourProblem((0, 0, 0), 21)
  288,706 nodes |  288,675 goal |   62 cost |  36,962 actions | GreenPourProblem((0, 0, 0), 21)
        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')
       27 nodes |       25 goal |  450 cost |      13 actions | RouteProblem('A', 'B')
      167 nodes |      173 goal |  910 cost |      82 actions | RouteProblem('N', 'L')
      117 nodes |      120 goal |  837 cost |      56 actions | RouteProblem('E', 'T')
      108 nodes |      109 goal |  572 cost |      44 actions | RouteProblem('O', 'M')
      116 nodes |      118 goal |    5 cost |      47 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),
1,175,305 nodes |1,175,130 goal | 2985 cost | 151,632 actions | TOTAL

depth_limited_search:
    4,433 nodes |    4,374 goal |   10 cost |     627 actions | PourProblem((1, 1, 1), 13)
    4,433 nodes |    4,374 goal |   30 cost |     627 actions | GreenPourProblem((1, 1, 1), 13)
   37,149 nodes |   37,106 goal |   10 cost |   4,753 actions | PourProblem((0, 0, 0), 21)
   37,149 nodes |   37,106 goal |   54 cost |   4,753 actions | GreenPourProblem((0, 0, 0), 21)
      452 nodes |      453 goal |  inf cost |     110 actions | PourProblem((0, 0), 8)
      452 nodes |      453 goal |  inf cost |     110 actions | GreenPourProblem((0, 0), 8)
   37,149 nodes |   37,106 goal |   10 cost |   4,753 actions | PourProblem((0, 0, 0), 21)
   37,149 nodes |   37,106 goal |   54 cost |   4,753 actions | GreenPourProblem((0, 0, 0), 21)
        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')
       17 nodes |        8 goal |  733 cost |      14 actions | RouteProblem('A', 'B')
       40 nodes |       38 goal |  910 cost |      26 actions | RouteProblem('N', 'L')
       29 nodes |       23 goal |  992 cost |      20 actions | RouteProblem('E', 'T')
       35 nodes |       29 goal |  895 cost |      22 actions | RouteProblem('O', 'M')
      351 nodes |      349 goal |    5 cost |     138 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),
  158,838 nodes |  158,526 goal |  inf cost |  20,706 actions | TOTAL

greedy_bfs:
      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)
    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)
      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)
      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)
        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')
        9 nodes |        4 goal |  450 cost |       6 actions | RouteProblem('A', 'B')
       29 nodes |       12 goal |  910 cost |      20 actions | RouteProblem('N', 'L')
       19 nodes |        8 goal |  837 cost |      14 actions | RouteProblem('E', 'T')
       14 nodes |        6 goal |  572 cost |      10 actions | RouteProblem('O', 'M')
       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),
   18,120 nodes |    2,082 goal | 2897 cost |   2,184 actions | TOTAL

weighted_astar_search:
      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)
    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)
      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)
      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)
        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')
        9 nodes |        4 goal |  450 cost |       6 actions | RouteProblem('A', 'B')
       32 nodes |       14 goal |  910 cost |      22 actions | RouteProblem('N', 'L')
       29 nodes |       12 goal |  805 cost |      19 actions | RouteProblem('E', 'T')
       18 nodes |        8 goal |  445 cost |      12 actions | RouteProblem('O', 'M')
       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),
   18,137 nodes |    2,090 goal | 2738 cost |   2,193 actions | TOTAL

extra_weighted_astar_search:
      948 nodes |      109 goal |    4 cost |     112 actions | PourProblem((1, 1, 1), 13)
    1,696 nodes |      190 goal |   10 cost |     204 actions | GreenPourProblem((1, 1, 1), 13)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)
      124 nodes |       30 goal |   14 cost |      43 actions | PourProblem((0, 0), 8)
      124 nodes |       30 goal |   35 cost |      45 actions | GreenPourProblem((0, 0), 8)
    3,499 nodes |      389 goal |    9 cost |     397 actions | PourProblem((0, 0, 0), 21)
    4,072 nodes |      454 goal |   21 cost |     463 actions | GreenPourProblem((0, 0, 0), 21)
        0 nodes |        1 goal |    0 cost |       0 actions | RouteProblem('A', 'A')
        9 nodes |        4 goal |  450 cost |       6 actions | RouteProblem('A', 'B')
       29 nodes |       12 goal |  910 cost |      20 actions | RouteProblem('N', 'L')
       23 nodes |        9 goal |  805 cost |      16 actions | RouteProblem('E', 'T')
       18 nodes |        8 goal |  445 cost |      12 actions | RouteProblem('O', 'M')
       15 nodes |        6 goal |    5 cost |      10 actions | EightPuzzle((1, 4, 2, 0, 7, 5, 3, 6, 8),
   18,128 nodes |    2,085 goal | 2738 cost |   2,188 actions | TOTAL
"""

def parse_data(data):
    """Parses the input text data into a structured dictionary."""
    
    
    algorithms = {}
    current_algorithm = None

    for line in data.strip().split('\n'):
        line = line.strip()
        if line.endswith(':'):
            current_algorithm = line[:-1]
            algorithms[current_algorithm] = []
        elif current_algorithm and line:
            parts = line.split('|')
            if len(parts) >= 5:
                try:
                    nodes = int(parts[0].strip().replace(',', ''))
                    goal = int(parts[1].strip().replace(',', ''))
                    cost = parts[2].strip().split()[0]
                    cost = float(cost) if cost != 'inf' else float('inf')
                    actions = int(parts[3].strip().replace(',', ''))
                    problem = parts[4].strip()
                    
                    algorithms[current_algorithm].append({
                        'nodes': nodes,
                        'goal': goal,
                        'cost': cost,
                        'actions': actions,
                        'problem': problem
                    })
                except ValueError:
                    pass
            
    return algorithms


def create_grouped_problem_charts(algorithms):
  
    all_problems = set()
    for algo_data in algorithms.values():
      for entry in algo_data:
        all_problems.add(entry['problem'])
    
    all_problems= list(all_problems)
    
    for problem in all_problems:
      problem_data = {
        algo: [entry for entry in data if entry['problem'] == problem]
          for algo, data in algorithms.items()
      }
      if any(problem_data.values()):
        print(f"Creating charts for problem: {problem}")
        
        df_problem = pd.DataFrame.from_dict(problem_data, orient='index').transpose()
        df_problem = df_problem.dropna(how='all')
        
        metrics = ['nodes','goal','cost','actions']

        fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(15,10))
        axes = axes.flatten()

        for i, metric in enumerate(metrics):
            metric_data = df_problem.apply(lambda row: [entry[metric] if isinstance(entry,dict) else None for entry in row], axis =1)
            
            metric_data_clean = metric_data.apply(lambda x: [value for value in x if value is not None])
            metric_data_clean = metric_data_clean.apply(lambda x: x if len(x)>0 else [0])
            
            df_temp = pd.DataFrame(metric_data_clean.tolist(), index = df_problem.index, columns = list(algorithms.keys()))

            df_temp.plot(kind='bar',ax=axes[i])
            axes[i].set_title(f'{metric.capitalize()} by Algorithm for {problem}')
            axes[i].set_ylabel(metric.capitalize())
            axes[i].set_xlabel('Index')
            axes[i].tick_params(axis='x', rotation=45)
            axes[i].legend(title='Algorithms',fontsize='small')

        plt.tight_layout()
        plt.show()

def create_grouped_algorithm_charts(algorithms):
    metrics = ['nodes', 'goal', 'cost', 'actions']
    for algo, algo_data in algorithms.items():
      print(f"Creating charts for algorithm: {algo}")
      df_algo = pd.DataFrame(algo_data)

      fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(15, 10))
      axes = axes.flatten()

      for i, metric in enumerate(metrics):
          df_algo.plot(kind = 'bar', x = 'problem',y = metric, ax = axes[i], legend=False)
          axes[i].set_title(f'{metric.capitalize()} by Problem for {algo}')
          axes[i].set_ylabel(metric.capitalize())
          axes[i].set_xlabel('Problem')
          axes[i].tick_params(axis='x', rotation=45)
          
      plt.tight_layout()
      plt.show()


algorithms = parse_data(data)
create_grouped_problem_charts(algorithms)
create_grouped_algorithm_charts(algorithms)