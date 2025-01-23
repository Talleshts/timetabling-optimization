#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ilcplex/cplex.h>    // CPLEX API
#include "gurobi_c.h"        // Gurobi API

#define MAX_LINE 2560
#define MAX_ITEMS 1000

// Estruturas de dados
typedef struct {
    char id[50];
    char name[50];
} Time;

typedef struct {
    char id[50];
    char name[50];
    char type[50];
} Resource;

typedef struct {
    char id[50];
    char name[50];
    int duration;
    char class_ref[50];
    char teacher_ref[50];
} Event;

// Função para leitura do TXT
void read_txt(const char *filename, Time times[], int *time_count, 
              Resource resources[], int *resource_count, Event events[], int *event_count) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        printf("Erro ao abrir o arquivo.\n");
        exit(1);
    }

    char line[MAX_LINE];
    char section[MAX_LINE] = "";
    while (fgets(line, sizeof(line), file)) {
        if (strncmp(line, "Times:", 6) == 0) {
            strcpy(section, "Times");
            continue;
        } else if (strncmp(line, "Resources:", 10) == 0) {
            strcpy(section, "Resources");
            continue;
        } else if (strncmp(line, "Events:", 7) == 0) {
            strcpy(section, "Events");
            continue;
        }

        // Processar a linha com base na seção atual
        if (strcmp(section, "Times") == 0) {
            sscanf(line, "%[^,], %[^\n]", times[*time_count].id, times[*time_count].name);
            (*time_count)++;
        } else if (strcmp(section, "Resources") == 0) {
            sscanf(line, "%[^,], %[^,], %[^\n]", resources[*resource_count].id, 
                   resources[*resource_count].name, resources[*resource_count].type);
            (*resource_count)++;
        } else if (strcmp(section, "Events") == 0) {
            sscanf(line, "%[^,], %[^,], %d, %[^,], %[^\n]", events[*event_count].id, 
                   events[*event_count].name, &events[*event_count].duration, 
                   events[*event_count].class_ref, events[*event_count].teacher_ref);
            (*event_count)++;
        }
    }

    fclose(file);
}

void solve_with_cplex(int num_events, int num_times, double **costs) {
    CPXENVptr env = NULL;
    CPXLPptr lp = NULL;
    int status;
    int num_vars = num_events * num_times;
    double one = 1.0;

    // Iniciar o ambiente
    env = CPXopenCPLEX(&status);
    if (status) {
        fprintf(stderr, "Erro ao iniciar o CPLEX.\n");
        return;
    }

    // Criar o modelo
    lp = CPXcreateprob(env, &status, "Timetable");
    if (status) {
        fprintf(stderr, "Erro ao criar o modelo no CPLEX.\n");
        CPXcloseCPLEX(&env);
        return;
    }

    // Adicionar variáveis (x_ij para evento i no horário j)
    double *obj = (double *)malloc(num_vars * sizeof(double));
    char *ctype = (char *)malloc(num_vars * sizeof(char));
    for (int i = 0; i < num_events; i++) {
        for (int j = 0; j < num_times; j++) {
            obj[i * num_times + j] = costs[i][j]; // Custo para evento i no horário j
            ctype[i * num_times + j] = 'B';       // Variável binária
        }
    }
    status = CPXnewcols(env, lp, num_vars, obj, NULL, NULL, ctype, NULL);
    if (status) {
        fprintf(stderr, "Erro ao adicionar variáveis no CPLEX.\n");
        CPXfreeprob(env, &lp);
        CPXcloseCPLEX(&env);
        return;
    }

    // Adicionar restrições
    // Exemplo: Cada evento deve ser alocado exatamente uma vez
    for (int i = 0; i < num_events; i++) {
        int *indices = (int *)malloc(num_times * sizeof(int));
        double *values = (double *)malloc(num_times * sizeof(double));
        for (int j = 0; j < num_times; j++) {
            indices[j] = i * num_times + j;
            values[j] = 1.0;
        }
        int rmatbeg = 0;
        status = CPXaddrows(env, lp, 0, 1, num_times, &one, "E", &rmatbeg, indices, values, NULL, NULL);
        free(indices);
        free(values);
    }

    // Resolver o modelo
    status = CPXmipopt(env, lp);
    if (status) {
        fprintf(stderr, "Erro ao resolver o modelo no CPLEX.\n");
    } else {
        printf("Modelo resolvido com sucesso no CPLEX.\n");
    }

    // Limpar memória
    free(obj);
    free(ctype);
    CPXfreeprob(env, &lp);
    CPXcloseCPLEX(&env);
}

void solve_with_gurobi(int num_events, int num_times, double **costs) {
    GRBenv *env = NULL;
    GRBmodel *model = NULL;
    int status;
    int num_vars = num_events * num_times;

    // Iniciar o ambiente
    status = GRBloadenv(&env, "Timetable.log");
    if (status) {
        fprintf(stderr, "Erro ao iniciar o Gurobi.\n");
        return;
    }

    // Criar o modelo
    status = GRBnewmodel(env, &model, "Timetable", 0, NULL, NULL, NULL, NULL, NULL);
    if (status) {
        fprintf(stderr, "Erro ao criar o modelo no Gurobi.\n");
        GRBfreeenv(env);
        return;
    }

    // Adicionar variáveis (x_ij para evento i no horário j)
    for (int i = 0; i < num_events; i++) {
        for (int j = 0; j < num_times; j++) {
            char var_name[20];
            sprintf(var_name, "x_%d_%d", i, j);
            status = GRBaddvar(model, 0, NULL, NULL, costs[i][j], 0, 1, GRB_BINARY, var_name);
            if (status) {
                fprintf(stderr, "Erro ao adicionar variável %s no Gurobi.\n", var_name);
            }
        }
    }
    GRBupdatemodel(model);

    // Adicionar restrições
    // Exemplo: Cada evento deve ser alocado exatamente uma vez
    for (int i = 0; i < num_events; i++) {
        int *indices = (int *)malloc(num_times * sizeof(int));
        double *values = (double *)malloc(num_times * sizeof(double));
        for (int j = 0; j < num_times; j++) {
            indices[j] = i * num_times + j;
            values[j] = 1.0;
        }
        status = GRBaddconstr(model, num_times, indices, values, GRB_EQUAL, 1.0, NULL);
        free(indices);
        free(values);
        if (status) {
            fprintf(stderr, "Erro ao adicionar restrição no Gurobi.\n");
        }
    }

    // Resolver o modelo
    status = GRBoptimize(model);
    if (status) {
        fprintf(stderr, "Erro ao resolver o modelo no Gurobi.\n");
    } else {
        printf("Modelo resolvido com sucesso no Gurobi.\n");
    }

    // Limpar memória
    GRBfreemodel(model);
    GRBfreeenv(env);
}

int main() {
    Time times[MAX_ITEMS];
    Resource resources[MAX_ITEMS];
    Event events[MAX_ITEMS];
    int time_count = 0, resource_count = 0, event_count = 0;

    // Ler o arquivo TXT
    read_txt("./instanciasParaSolver/output.txt", times, &time_count, resources, &resource_count, events, &event_count);

    // Exibir os dados lidos (opcional, para validação)
    printf("Times:\n");
    for (int i = 0; i < time_count; i++) {
        printf("ID: %s, Name: %s\n", times[i].id, times[i].name);
    }

    printf("\nResources:\n");
    for (int i = 0; i < resource_count; i++) {
        printf("ID: %s, Name: %s, Type: %s\n", resources[i].id, resources[i].name, resources[i].type);
    }

    printf("\nEvents:\n");
    for (int i = 0; i < event_count; i++) {
        printf("ID: %s, Name: %s, Duration: %d, Class: %s, Teacher: %s\n",
               events[i].id, events[i].name, events[i].duration, 
               events[i].class_ref, events[i].teacher_ref);
    }

    // Criar matriz de custos (exemplo)
    double **costs = (double **)malloc(event_count * sizeof(double *));
    for (int i = 0; i < event_count; i++) {
        costs[i] = (double *)malloc(time_count * sizeof(double));
        for (int j = 0; j < time_count; j++) {
            costs[i][j] = 1.0; // Exemplo de custo
        }
    }

    // solve_with_cplex(event_count, time_count, costs);
    solve_with_gurobi(event_count, time_count, costs);

    // Limpar memória da matriz de custos
    for (int i = 0; i < event_count; i++) {
        free(costs[i]);
    }
    free(costs);

    return 0;
}