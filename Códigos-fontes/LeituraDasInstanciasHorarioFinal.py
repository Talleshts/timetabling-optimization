import xml.etree.ElementTree as ET
import re

# Estruturas de dados para armazenar informações
times = []
resources = []
events = []
constraints = []

# Função para processar os horários
def parse_times(times_element):
    for time in times_element.findall("Time"):
        time_id = time.get("Id")
        name = time.find("Name").text if time.find("Name") is not None else ""
        times.append({"id": time_id, "name": name})

# Função para processar os recursos
def parse_resources(resources_element):
    for resource in resources_element.findall("Resource"):
        resource_id = resource.get("Id")
        name = resource.find("Name").text if resource.find("Name") is not None else ""
        resource_type = resource.find("ResourceType").get("Reference") if resource.find("ResourceType") is not None else ""
        resources.append({"id": resource_id, "name": name, "type": resource_type})

# Função para processar os eventos
def parse_events(events_element):
    for event in events_element.findall("Event"):
        event_id = event.get("Id")
        name = event.find("Name").text if event.find("Name") is not None else ""
        duration = int(event.find("Duration").text) if event.find("Duration") is not None else 0
        max_daily = int(event.find("MaxDaily").text) if event.find("MaxDaily") is not None else 0
        double_lessons = int(event.find("DoubleLessons").text) if event.find("DoubleLessons") is not None else 0
        class_ref = ""
        teacher_ref = ""
        for resource in event.findall("./Resources/Resource"):
            role = resource.get("Role")
            if role == "Class":
                class_ref = resource.get("Reference")
            elif role == "Teacher":
                teacher_ref = resource.get("Reference")
        events.append({
            "id": event_id, "name": name, "duration": duration,
            "max_daily": max_daily, "double_lessons": double_lessons,
            "class": class_ref, "teacher": teacher_ref
        })

# Função para processar restrições
def parse_constraints(constraints_element):
    for constraint in constraints_element:
        constraint_id = constraint.get("Id")
        name = constraint.find("Name").text if constraint.find("Name") is not None else ""
        required = constraint.find("Required").text.lower() == "true"
        weight = float(constraint.find("Weight").text) if constraint.find("Weight") is not None else 1.0
        constraints.append({"id": constraint_id, "name": name, "required": required, "weight": weight})

# Função para gerar o arquivo LP
def generate_lp_file(output_path):
    delta = 9.0  # Peso para dias de trabalho
    gamma = 3.0  # Peso para tempos ociosos
    omega = 1.0  # Peso para lições duplas

    with open(output_path, "w") as f:
        # Escrever a função objetivo
        f.write("Minimize\n")
        f.write(f" obj: {delta} sum_idle + {gamma} sum_days + {omega} sum_double\n\n")

        # Escrever as restrições
        f.write("Subject To\n")

        # H1: Carga horária de cada evento deve ser atendida
        for event in events:
            terms = [f"x_{event['teacher']}_{event['class']}_{time['id']}" for time in times]
            f.write(f" h1_{event['id']}: " + " + ".join(terms) + f" = {event['duration']}\n")

        # H2: Evitar conflitos de horários para professores
        for teacher in [r for r in resources if r['type'] == "Teacher"]:
            for time in times:
                terms = [f"x_{teacher['id']}_{event['class']}_{time['id']}" for event in events if event['teacher'] == teacher['id']]
                f.write(f" h2_{teacher['id']}_{time['id']}: " + " + ".join(terms) + " <= 1\n")

        # H3: Limites diários de aulas por evento
        for event in events:
            for day in range(1, 6):  # Supondo 5 dias na semana
                terms = [f"x_{event['teacher']}_{event['class']}_{time['id']}" for time in times if time['id'].startswith(f"D{day}")]
                f.write(f" h3_{event['id']}_D{day}: " + " + ".join(terms) + f" <= {event['max_daily']}\n")

        # H4: Indisponibilidade de professores
        for teacher in [r for r in resources if r['type'] == "Teacher"]:
            for time in times:
                availability = 1  # Ajuste com base no XML se necessário
                if availability == 0:
                    terms = [f"x_{teacher['id']}_{event['class']}_{time['id']}" for event in events if event['teacher'] == teacher['id']]
                    f.write(f" h4_{teacher['id']}_{time['id']}: " + " + ".join(terms) + " = 0\n")

        # H5: Lições duplas
        for event in events:
            terms = []
            for time in times:
                match = re.search(r'(\D+)(\d+)', time['id'])  # Captura prefixo e número (e.g., "Mon" e "1")
                if match:
                    prefix, num = match.groups()
                    next_id = f"{prefix}{int(num) + 1}"  # Incrementa a parte numérica e recria o ID
                    if next_id in [t['id'] for t in times]:
                        terms.append(f"x_{event['teacher']}_{event['class']}_{time['id']} * x_{event['teacher']}_{event['class']}_{next_id}")
            if terms:
                f.write(f" h5_{event['id']}: " + " + ".join(terms) + f" >= {event['double_lessons']}\n")


        # S1 e S2: Dias de trabalho e tempos ociosos
        for teacher in [r for r in resources if r['type'] == "Teacher"]:
            for day in range(1, 6):  # Supondo 5 dias
                terms = [f"x_{teacher['id']}_*_{time['id']}" for time in times if time['id'].startswith(f"D{day}")]
                f.write(f" s1_s2_{teacher['id']}_D{day}: " + " + ".join(terms) + " <= 1\n")

        # Variáveis binárias
        f.write("\nBinary\n")
        for event in events:
            for time in times:
                f.write(f" x_{event['teacher']}_{event['class']}_{time['id']}\n")

        # Finalizar o arquivo
        f.write("End\n")

# Função principal para processar o XML e gerar o LP
def parse_xml_and_generate_lp(file_path, output_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Processar os elementos do XML
    times_element = root.find(".//Times")
    if times_element is not None:
        parse_times(times_element)

    resources_element = root.find(".//Resources")
    if resources_element is not None:
        parse_resources(resources_element)

    events_element = root.find(".//Events")
    if events_element is not None:
        parse_events(events_element)

    constraints_element = root.find(".//Constraints")
    if constraints_element is not None:
        parse_constraints(constraints_element)

    # Gerar o arquivo LP
    generate_lp_file(output_path)

# Executar o parser e gerar o LP
parse_xml_and_generate_lp("./Instâncias/BrazilInstance7.xml", "./BrazilInstance7.lp")
