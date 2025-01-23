#include <iostream>
#include <iomanip>
#include <vector>
#include <chrono>
#include <ilcplex/cplex.h>    // CPLEX API
#include "gurobi_c++.h"         // Gurobi API

struct Result {
    std::string instance;
    double lb_cplex, ub_cplex, gap_cplex, time_cplex;
    double lb_gurobi, ub_gurobi, gap_gurobi, time_gurobi;
};

void solve_with_cplex(const std::string &lp_file, Result &result) {
    CPXENVptr env = NULL;
    CPXLPptr lp = NULL;
    int status;

    auto start_time = std::chrono::high_resolution_clock::now();

    // Iniciar o ambiente CPLEX
    env = CPXopenCPLEX(&status);
    if (status) {
        std::cerr << "Erro ao iniciar o CPLEX." << std::endl;
        return;
    }

    // Ler o problema LP
    lp = CPXcreateprob(env, &status, "Timetable");
    status = CPXreadcopyprob(env, lp, lp_file.c_str(), NULL);
    if (status) {
        std::cerr << "Erro ao carregar o arquivo LP no CPLEX." << std::endl;
        CPXcloseCPLEX(&env);
        return;
    }

    // Resolver o modelo
    status = CPXmipopt(env, lp);
    if (status) {
        std::cerr << "Erro ao resolver o modelo no CPLEX." << std::endl;
        CPXfreeprob(env, &lp);
        CPXcloseCPLEX(&env);
        return;
    }

    // Coletar resultados
    double lb, ub;
    status = CPXgetbestobjval(env, lp, &lb);  // Limitante inferior
    status = CPXgetobjval(env, lp, &ub);     // Limitante superior

    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end_time - start_time;

    result.lb_cplex = lb;
    result.ub_cplex = ub;
    result.gap_cplex = ((ub - lb) / ub) * 100.0;
    result.time_cplex = elapsed.count();

    // Liberar memória
    CPXfreeprob(env, &lp);
    CPXcloseCPLEX(&env);
}

void solve_with_gurobi(const std::string &lp_file, Result &result) {
    GRBenv *env = NULL;
    GRBmodel *model = NULL;
    int status;

    auto start_time = std::chrono::high_resolution_clock::now();

    // Iniciar o ambiente Gurobi
    status = GRBloadenv(&env, "Timetable.log");
    if (status) {
        std::cerr << "Erro ao iniciar o Gurobi." << std::endl;
        return;
    }

    // Ler o modelo LP do arquivo
    status = GRBreadmodel(env, lp_file.c_str(), &model);  // Corrigido aqui
    if (status) {
        std::cerr << "Erro ao carregar o arquivo LP no Gurobi." << std::endl;
        GRBfreeenv(env);
        return;
    }

    // Resolver o modelo
    status = GRBoptimize(model);
    if (status) {
        std::cerr << "Erro ao resolver o modelo no Gurobi." << std::endl;
        GRBfreemodel(model);
        GRBfreeenv(env);
        return;
    }

    // Coletar resultados
    double lb, ub;
    status = GRBgetdblattr(model, GRB_DBL_ATTR_OBJBOUND, &lb);  // Limitante inferior
    status = GRBgetdblattr(model, GRB_DBL_ATTR_OBJVAL, &ub);    // Limitante superior

    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end_time - start_time;

    result.lb_gurobi = lb;
    result.ub_gurobi = ub;
    result.gap_gurobi = ((ub - lb) / ub) * 100.0;
    result.time_gurobi = elapsed.count();

    // Liberar memória
    GRBfreemodel(model);
    GRBfreeenv(env);
}


void print_results(const std::vector<Result> &results) {
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "Tabela 1 – Resultados obtidos pelos métodos exatos\n";
    std::cout << "Instância\tCPLEX\t\t\t\tGurobi\n";
    std::cout << "        \tLB\tUB\tGAP (%)\tTEMPO\tLB\tUB\tGAP (%)\tTEMPO\n";

    double sum_lb_cplex = 0, sum_ub_cplex = 0, sum_gap_cplex = 0, sum_time_cplex = 0;
    double sum_lb_gurobi = 0, sum_ub_gurobi = 0, sum_gap_gurobi = 0, sum_time_gurobi = 0;

    for (const auto &result : results) {
        std::cout << result.instance << "\t"
                  << result.lb_cplex << "\t" << result.ub_cplex << "\t" << result.gap_cplex << "\t" << result.time_cplex << "\t"
                  << result.lb_gurobi << "\t" << result.ub_gurobi << "\t" << result.gap_gurobi << "\t" << result.time_gurobi << "\n";

        sum_lb_cplex += result.lb_cplex;
        sum_ub_cplex += result.ub_cplex;
        sum_gap_cplex += result.gap_cplex;
        sum_time_cplex += result.time_cplex;

        sum_lb_gurobi += result.lb_gurobi;
        sum_ub_gurobi += result.ub_gurobi;
        sum_gap_gurobi += result.gap_gurobi;
        sum_time_gurobi += result.time_gurobi;
    }

    int num_instances = results.size();
    std::cout << "MÉDIA\t\t"
              << sum_lb_cplex / num_instances << "\t" << sum_ub_cplex / num_instances << "\t"
              << sum_gap_cplex / num_instances << "\t" << sum_time_cplex / num_instances << "\t"
              << sum_lb_gurobi / num_instances << "\t" << sum_ub_gurobi / num_instances << "\t"
              << sum_gap_gurobi / num_instances << "\t" << sum_time_gurobi / num_instances << "\n";
}

int main() {
    std::vector<std::string> instances = {"./output/BrazilInstance1.lp"}; // Lista de instâncias
    std::vector<Result> results;

    for (const auto &instance : instances) {
        Result result;
        result.instance = instance;

        // Resolver com CPLEX
        solve_with_cplex(instance, result);

        // Resolver com Gurobi
        solve_with_gurobi(instance, result);

        results.push_back(result);
    }

    // Exibir os resultados
    print_results(results);

    return 0;
}
