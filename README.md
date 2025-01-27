# timetabling-optimization
Projeto de otimização de instâncias para horários escolares do ensino médio

# Explicação do Problema de Otimização

## Função Objetivo

O objetivo do problema é **minimizar o custo total** associado à criação de horários escolares, considerando três componentes principais:

1. **Custo por aulas duplas não atendidas** ($\delta g_{tc}$): Cada aula dupla que não é atendida adiciona um custo fixo ao total.
2. **Custo por períodos ociosos** ($\omega x_{ta}$): Cada período em que o professor está ocioso gera um custo adicional.
3. **Custo por dias de trabalho** ($\gamma x_{ta}$): Cada dia em que o professor trabalha adiciona um custo fixo ao total.

A função objetivo é representada como:

$$
\text{Minimizar:} \quad \sum_{t \in T} \left( \sum_{c \in C} \delta g_{tc} + \sum_{a \in W_t} \omega x_{ta} + \sum_{a \in Y_t} \gamma x_{ta} \right)
$$

---

## Restrições

As restrições representam as condições que precisam ser atendidas para criar um cronograma válido. Aqui estão elas:

### 1. Conservação de Fluxo

Para cada professor ($t$) e nó ($v$), a diferença entre o número de arcos que entram e saem deve ser igual a um valor específico ($b_v$):

$$
\sum_{a \in A^+_{tv}} x_{ta} - \sum_{a \in A^-_{tv}} x_{ta} = b_v, \quad \forall t \in T, v \in V
$$

Onde:
- $b_v = 1$ se o nó é a origem (início do trajeto do professor).
- $b_v = -1$ se o nó é o destino (final do trajeto do professor).
- Caso contrário, $b_v = 0$.

Essa restrição garante que os professores só percorrem trajetos válidos entre aulas, sem interrupções ou nós desconectados.

### 2. Cada Aula é Atribuída no Máximo Uma Vez

Uma aula para uma turma ($c$), em um dia ($d$) e período ($p$), pode ser alocada no máximo uma vez:

$$
\sum_{t \in T} \sum_{a \in A_{tcdp}} x_{ta} \leq 1, \quad \forall c \in C, d \in D, p \in P
$$

### 3. Número de Aulas Obrigatórias

Para cada professor ($t$) e turma ($c$), o número total de aulas alocadas deve ser igual ao número de aulas planejadas ($H_{tc}$):

$$
\sum_{a \in \bigcup_{d \in D, p \in P} A_{tcdp}} S_{ta} x_{ta} = H_{tc}, \quad \forall t \in T, c \in C
$$

### 4. Máximo de Aulas Diárias

Para cada professor ($t$) e turma ($c$), o número de aulas em um único dia não pode ultrapassar o limite diário permitido ($L_{tc}$):

$$
\sum_{a \in \bigcup_{p \in P} A_{tcdp}} S_{ta} x_{ta} \leq L_{tc}, \quad \forall t \in T, c \in C, d \in D
$$

### 5. Aulas no Primeiro Período do Dia

Para o primeiro período do dia ($h = 1$), apenas uma aula pode ser atribuída, respeitando a regra de inicialização de horários:

$$
\sum_{a \in \bigcup_{p \in P} A_{tcdp}} x_{ta} \leq 1, \quad \forall t \in T, c \in C, d \in D, h = 1
$$

### 6. Aulas Duplas Não Atendidas

O número de aulas duplas não atendidas para cada professor ($t$) e turma ($c$) deve ser maior ou igual à diferença entre o número mínimo necessário ($M_{tc}$) e o número de aulas duplas efetivamente atribuídas:

$$
 g_{tc} \geq M_{tc} - \sum_{a \in G_{tc}} x_{ta}, \quad \forall t \in T, c \in C
$$

### 7. Mínimo de Dias de Trabalho

Para cada professor ($t$), o número de dias de trabalho efetivos deve ser maior ou igual ao mínimo exigido ($Y'_t$):

$$
\sum_{a \in Y_t} x_{ta} \geq Y'_t, \quad \forall t \in T
$$

### 8. Definição das Variáveis

- As variáveis $x_{ta}$ são binárias, indicando se o professor ($t$) utiliza um arco ($a$) ou não:
  $$
  x_{ta} \in \{0, 1\}, \quad \forall t \in T, a \in A_t
  $$

- As variáveis $g_{tc}$ são contínuas e indicam o número de aulas duplas não atendidas:
  $$
  g_{tc} \geq 0, \quad \forall t \in T, c \in C
  $$

---

## Resumo Verbal

O problema busca criar um cronograma escolar que minimize os custos totais de aulas duplas não atendidas, períodos ociosos e dias de trabalho dos professores, enquanto respeita as seguintes restrições:
- Os professores percorrem trajetos válidos entre aulas.
- Cada aula é atribuída no máximo uma vez.
- O número total de aulas e o máximo diário são respeitados.
- Aulas duplas e dias de trabalho mínimos são garantidos.
- As variáveis seguem suas definições específicas.
