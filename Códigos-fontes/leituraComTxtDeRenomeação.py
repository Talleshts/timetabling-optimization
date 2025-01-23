import xml.etree.ElementTree as ET
import re

# Estruturas de dados para armazenar informações
times = []
resources = []
events = []
constraints = []
variable_map = {}  # Mapear variáveis para índices
variable_counter = 0
constraint_map = {}  # Mapear restrições para índices
constraint_counter = 0

# Função para mapear uma variável para um índice
def map_variable(name):
    global variable_counter
    if name not in variable_map:
        variable_map[name] = f"v{variable_counter}"  # Nome da variável com índice
        variable_counter += 1
    return variable_map[name]

# Função para mapear uma restrição para um índice
def map_constraint(name):
    global constraint_counter
    if name not in constraint_map:
        constraint_map[name] = f"c{constraint_counter}"  # Nome da restrição com índice
        constraint_counter += 1
    return constraint_map[name]

# Função para processar os horários
def parse_times(times_element):
    for time in times_element.findall("Time"):
        time_id = time.get("Id")
        times.append({"id": time_id})

# Função para processar os recursos
def parse_resources(resources_element):
    for resource in resources_element.findall("Resource"):
        resource_id = resource.get("Id")
        resource_type = resource.find("ResourceType").get("Reference") if resource.find("ResourceType") is not None else ""
        resources.append({"id": resource_id, "type": resource_type})

# Função para processar os eventos
def parse_events(events_element):
    for event in events_element.findall("Event"):
        event_id = event.get("Id")
        duration = int(event.find("Duration").text) if event.find("Duration") is not None else 0
        max_daily = int(event.find("MaxDaily").text) if event.find("MaxDaily") is not None else 0
        double_lessons = int(event.find("DoubleLessons").text) if event.find("DoubleLessons") is not None else 0
        teacher = None
        cls = None
        for resource in event.findall("Resources/Resource"):
            role = resource.get("Role")
            if role == "Teacher":
                teacher = resource.get("Reference")
            elif role == "Class":
                cls = resource.get("Reference")
        events.append({
            "id": event_id,
            "duration": duration,
            "max_daily": max_daily,
            "double_lessons": double_lessons,
            "teacher": teacher,
            "class": cls
        })

# Função para processar restrições
def parse_constraints(constraints_element):
    for constraint in constraints_element:
        constraint_id = constraint.get("Id")
        name = constraint.find("Name").text if constraint.find("Name") is not None else ""
        constraints.append({"id": constraint_id, "name": name})

# Função para gerar o arquivo LP, a legenda e o mapeamento de restrições
def generate_lp_and_legend(lp_output_path, legend_output_path, constraints_output_path):
    global variable_map, constraint_map
    double_variables = set()  # Variáveis para lições duplas

    with open(lp_output_path, "w") as lp_file, open(legend_output_path, "w") as legend_file, open(constraints_output_path, "w") as constraints_file:
        # Função objetivo
        lp_file.write("Minimize\n obj: ")
        terms = []
        for teacher in [r for r in resources if r["type"] == "Teacher"]:
            terms.append("9 " + map_variable("days_" + teacher["id"]))
            terms.append("3 " + map_variable("idle_" + teacher["id"]))
        for event in events:
            terms.append("1 " + map_variable("double_" + event["id"]))
        lp_file.write(" + ".join(terms) + "\n\n")

        # Restrições
        lp_file.write("Subject To\n")

        # H1: Carga horária
        for event in events:
            if event["teacher"] and event["class"]:
                terms = [map_variable("x_" + event["teacher"] + "_" + event["class"] + "_" + time["id"]) for time in times]
                constraint_name = map_constraint("Carga horária do evento " + event["id"])
                lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " = " + str(event["duration"]) + "\n")

        # H2: Conflito de horário por professor
        for teacher in [r for r in resources if r["type"] == "Teacher"]:
            for time in times:
                terms = [map_variable("x_" + teacher["id"] + "_" + event["class"] + "_" + time["id"]) for event in events if event["teacher"] == teacher["id"] and event["class"]]
                constraint_name = map_constraint("Conflito de horário do professor " + teacher["id"] + " no tempo " + time["id"])
                lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " <= 1\n")

        # H3: Conflito de horário por turma
        for cls in {e["class"] for e in events if e["class"]}:
            for time in times:
                terms = [map_variable("x_" + event["teacher"] + "_" + cls + "_" + time["id"]) for event in events if event["class"] == cls and event["teacher"]]
                constraint_name = map_constraint("Conflito de horário da turma " + cls + " no tempo " + time["id"])
                lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " <= 1\n")

        # H4: Indisponibilidade dos professores
        for constraint in constraints:
            if constraint["name"] == "AvoidUnavailableTimes":
                for time in times:
                    terms = [map_variable("x_" + constraint["id"] + "_" + event["class"] + "_" + time["id"]) for event in events if event["teacher"] == constraint["id"] and event["class"]]
                    constraint_name = map_constraint("Indisponibilidade do professor " + constraint["id"] + " no tempo " + time["id"])
                    lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " = 0\n")

        # H5: Máximo de aulas diárias
        for event in events:
            if event["teacher"] and event["class"] and event["max_daily"]:
                daily_terms = {}
                for time in times:
                    day = time["id"][:2]  # Extrair o dia (e.g., Mo, Tu)
                    if day not in daily_terms:
                        daily_terms[day] = []
                    daily_terms[day].append(map_variable("x_" + event["teacher"] + "_" + event["class"] + "_" + time["id"]))
                for day, terms in daily_terms.items():
                    constraint_name = map_constraint("Máximo de aulas diárias do evento " + event["id"] + " no dia " + day)
                    lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " <= " + str(event["max_daily"]) + "\n")

        # H6: Lições duplas
        for event in events:
            if event["teacher"] and event["class"] and event["double_lessons"]:
                for i, time in enumerate(times[:-1]):
                    current_time = time["id"]
                    next_time = times[i + 1]["id"]
                    if current_time[:2] == next_time[:2]:  # Verificar se estão no mesmo dia
                        double_var = map_variable("double_" + event["id"] + "_" + current_time)
                        constraint_name = map_constraint("Lições duplas do evento " + event["id"] + " no tempo " + current_time)
                        lp_file.write(f" {constraint_name}: " + double_var + " - "
                                    + map_variable("x_" + event["teacher"] + "_" + event["class"] + "_" + current_time) + " - "
                                    + map_variable("x_" + event["teacher"] + "_" + event["class"] + "_" + next_time) + " >= -1\n")

        # S1: Períodos ociosos
        for teacher in [r for r in resources if r["type"] == "Teacher"]:
            for day in ["Mo", "Tu", "We", "Th", "Fr"]:
                day_periods = [time for time in times if time["id"].startswith(day)]
                for i in range(len(day_periods) - 1):
                    current = day_periods[i]["id"]
                    next_period = day_periods[i + 1]["id"]
                    idle_var = map_variable("idle_" + teacher["id"] + "_" + current)
                    constraint_name = map_constraint("Período ocioso do professor " + teacher["id"] + " no tempo " + current)
                    lp_file.write(f" {constraint_name}: " + idle_var + " - "
                                + map_variable("x_" + teacher["id"] + "_*_" + current) + " + "
                                + map_variable("x_" + teacher["id"] + "_*_" + next_period) + " >= 0\n")

        # S2: Dias de trabalho
        for teacher in [r for r in resources if r["type"] == "Teacher"]:
            for day in ["Mo", "Tu", "We", "Th", "Fr"]:
                terms = [map_variable("x_" + teacher["id"] + "_" + time["id"]) for time in times if time["id"].startswith(day)]
                constraint_name = map_constraint("Dias de trabalho do professor " + teacher["id"] + " no dia " + day)
                lp_file.write(f" {constraint_name}: " + map_variable("days_" + teacher["id"]) + " - " +
                            " - ".join(terms) + " >= 0\n")

        # S3: Lições duplas solicitadas
        for event in events:
            if event["double_lessons"]:
                terms = [map_variable("double_" + event["id"] + "_" + time["id"]) for time in times]
                constraint_name = map_constraint("Lições duplas solicitadas do evento " + event["id"])
                lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " >= " + str(event["double_lessons"]) + "\n")

        # Variáveis binárias
        binary_terms = []
        for event in events:
            if event["teacher"] and event["class"]:
                for time in times:
                    binary_terms.append(map_variable("x_" + event["teacher"] + "_" + event["class"] + "_" + time["id"]))
        binary_terms.extend(double_variables)

        if binary_terms:
            lp_file.write("\nBinary\n")
            for term in binary_terms:
                lp_file.write(" " + term + "\n")

        # Finalizar arquivo LP
        lp_file.write("End\n")

        # Gerar legenda
        legend_file.write("Legenda das Variáveis:\n")
        for original, mapped in variable_map.items():
            legend_file.write(mapped + ": " + original + "\n")

        # Gerar mapeamento de restrições
        constraints_file.write("Legenda das Restrições:\n")
        for original, mapped in constraint_map.items():
            constraints_file.write(mapped + ": " + original + "\n")

# Função principal para processar o XML e gerar os arquivos
def parse_xml_and_generate_files(file_path, lp_output_path, legend_output_path, constraints_output_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Processar os elementos do XML
    parse_times(root.find(".//Times"))
    parse_resources(root.find(".//Resources"))
    parse_events(root.find(".//Events"))
    parse_constraints(root.find(".//Constraints"))

    # Gerar arquivos LP, legenda e mapeamento de restrições
    generate_lp_and_legend(lp_output_path, legend_output_path, constraints_output_path)

# Executar o parser e gerar os arquivos
parse_xml_and_generate_files(
    "./Instâncias/BrazilInstance7.xml",
    "./outputs/lps/BrazilInstance7.lp",
    "./outputs/txt/BrazilInstance7_legend.txt",
    "./outputs/txt/BrazilInstance7_constraints.txt"
)
