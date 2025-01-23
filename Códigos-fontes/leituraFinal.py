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
            "id": event_id.replace("-", "_"), 
            "name": name, 
            "duration": duration,
            "max_daily": max_daily,  # Garantir que o campo esteja presente
            "double_lessons": double_lessons,  # Também adicionar DoubleLessons
            "class": class_ref.replace("-", "_"), 
            "teacher": teacher_ref.replace("-", "_")
        })

# Função para processar restrições
def parse_constraints(constraints_element):
    for constraint in constraints_element:
        constraint_id = constraint.get("Id").replace("-", "_")
        name = constraint.find("Name").text if constraint.find("Name") is not None else ""
        required = constraint.find("Required").text.lower() == "true"
        weight = float(constraint.find("Weight").text) if constraint.find("Weight") is not None else 1.0
        constraints.append({"id": constraint_id, "name": name, "required": required, "weight": weight})

# Função para gerar o arquivo LP
def generate_lp_file(output_path):
    double_variables = set()  # Inicializar a variável aqui
    with open(output_path, "w") as f:
        # Função objetivo
        f.write("Minimize\n obj: ")
        terms = []
        for teacher in [r for r in resources if r["type"] == "Teacher"]:
            terms.append(f"9 days_{teacher['id'].replace('-', '_')}")  # S2: Minimizar dias de trabalho
            terms.append(f"3 idle_{teacher['id'].replace('-', '_')}")  # S1: Evitar períodos ociosos
        for event in events:
            terms.append(f"1 double_{event['id'].replace('-', '_')}")  # S3: Lições duplas não atendidas
        f.write(" + ".join(terms) + "\n\n")

        # Restrições
        f.write("Subject To\n")
        
        # H1: Carga horária
        for event in events:
            terms = [f"x_{event['teacher'].replace('-', '_')}_{event['class'].replace('-', '_')}_{time['id'].replace('-', '_')}" for time in times]
            f.write(f" h1_{event['id'].replace('-', '_')}: " + " + ".join(terms) + f" = {event['duration']}\n")
        
        # H2: Conflito de horário por professor
        for teacher in [r for r in resources if r["type"] == "Teacher"]:
            for time in times:
                terms = [f"x_{teacher['id'].replace('-', '_')}_{event['class'].replace('-', '_')}_{time['id'].replace('-', '_')}" for event in events if event["teacher"] == teacher["id"]]
                f.write(f" h2_{teacher['id'].replace('-', '_')}_{time['id'].replace('-', '_')}: " + " + ".join(terms) + " <= 1\n")
        
        # H3: Conflito de horário por turma
        for cls in {e["class"] for e in events if e["class"]}:  # Adicionar verificação de classe
            for time in times:
                terms = [f"x_{event['teacher'].replace('-', '_')}_{cls.replace('-', '_')}_{time['id'].replace('-', '_')}" for event in events if event["class"] == cls]
                unique_terms = list(set(terms))  # Remover duplicatas
                f.write(f" h3_{cls.replace('-', '_')}_{time['id'].replace('-', '_')}: " + " + ".join(unique_terms) + " <= 1\n")
        
        # H4: Indisponibilidade
        for constraint in constraints:
            if constraint["name"] == "AvoidUnavailableTimes":
                for time in times:
                    terms = [f"x_{constraint['id'].replace('-', '_')}_{event['class'].replace('-', '_')}_{time['id'].replace('-', '_')}" for event in events if event["teacher"] == constraint["id"]]
                    if terms:  # Apenas se houver termos
                        f.write(f" h4_{constraint['id'].replace('-', '_')}_{time['id'].replace('-', '_')}: " + " + ".join(terms) + " = 0\n")

        # H5: Máximo de aulas diárias por evento
        for event in events:
            for day in ["Mo", "Tu", "We", "Th", "Fr"]:
                terms = [f"x_{event['teacher'].replace('-', '_')}_{event['class'].replace('-', '_')}_{time['id'].replace('-', '_')}" for time in times if time['id'].startswith(day)]
                if terms:
                    f.write(f" h5_{event['id'].replace('-', '_')}_{day}: " + " + ".join(terms) + f" <= {event['max_daily']}\n")
        
        # H6: Lições duplas (aulas consecutivas)
        for event in events:
            for time in times:
                match = re.search(r'(\D+)(\d+)', time['id'])
                if match:
                    prefix, num = match.groups()
                    next_id = f"{prefix}{int(num) + 1}"
                    if next_id in [t['id'] for t in times]:
                        double_var = f"double_{event['id'].replace('-', '_')}_{time['id'].replace('-', '_')}"
                        double_variables.add(double_var)
                        f.write(f" h6_{event['id'].replace('-', '_')}_{time['id'].replace('-', '_')}: {double_var} - x_{event['teacher'].replace('-', '_')}_{event['class'].replace('-', '_')}_{time['id'].replace('-', '_')} - x_{event['teacher'].replace('-', '_')}_{event['class'].replace('-', '_')}_{next_id.replace('-', '_')} <= 0\n")
                        f.write(f" h6_aux_{event['id'].replace('-', '_')}_{time['id'].replace('-', '_')}: {double_var} <= 1\n")

        # S1: Períodos ociosos
        for teacher in [r for r in resources if r["type"] == "Teacher"]:
            for day in ["Mo", "Tu", "We", "Th", "Fr"]:
                day_periods = [time for time in times if time['id'].startswith(day)]
                for i in range(len(day_periods) - 1):
                    current = day_periods[i]["id"]
                    next_period = day_periods[i + 1]["id"]
                    f.write(f" s1_{teacher['id'].replace('-', '_')}_{current.replace('-', '_')}: idle_{teacher['id'].replace('-', '_')}_{current.replace('-', '_')} - x_{teacher['id'].replace('-', '_')}_{current.replace('-', '_')} + x_{teacher['id'].replace('-', '_')}_{next_period.replace('-', '_')} >= 0\n")

        # S2: Dias de trabalho
        for teacher in [r for r in resources if r["type"] == "Teacher"]:
            for day in ["Mo", "Tu", "We", "Th", "Fr"]:
                terms = [f"x_{teacher['id'].replace('-', '_')}_{time['id'].replace('-', '_')}" for time in times if time['id'].startswith(day)]
                if terms:
                    f.write(f" s2_{teacher['id'].replace('-', '_')}_{day}: days_{teacher['id'].replace('-', '_')} - " + " - ".join(terms) + " >= 0\n")

        # S3: Atender ao número de lições duplas solicitadas
        for event in events:
            terms = [f"double_{event['id'].replace('-', '_')}_{time['id'].replace('-', '_')}" for time in times if f"double_{event['id'].replace('-', '_')}_{time['id'].replace('-', '_')}" in double_variables]
            if terms:
                f.write(f" s3_{event['id'].replace('-', '_')}: " + " + ".join(terms) + f" >= {event['double_lessons']}\n")

        # Variáveis binárias
        f.write("\nBinary\n")
        for event in events:
            for time in times:
                f.write(f" x_{event['teacher'].replace('-', '_')}_{event['class'].replace('-', '_')}_{time['id'].replace('-', '_')}\n")
        for double_var in double_variables:
            f.write(f" {double_var}\n")

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
parse_xml_and_generate_lp("./Instâncias/BrazilInstance1.xml", "./outputs/BrazilInstance1.lp")