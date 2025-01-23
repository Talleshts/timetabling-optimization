import xml.etree.ElementTree as ET

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
        class_ref = ""
        teacher_ref = ""
        for resource in event.findall("./Resources/Resource"):
            role = resource.get("Role")
            if role == "Class":
                class_ref = resource.get("Reference")
            elif role == "Teacher":
                teacher_ref = resource.get("Reference")
        events.append({"id": event_id, "name": name, "duration": duration, "class": class_ref, "teacher": teacher_ref})

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
    delta = 9.0
    gamma = 3.0
    omega = 1.0

    with open(output_path, "w") as f:
        # Escrever a função objetivo
        f.write("Minimize\n")
        f.write(f" obj: {delta} * sum_doubles + {gamma} * sum_days + {omega} * sum_idle\n\n")

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

        # Restrições adicionais...

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
parse_xml_and_generate_lp("./Instâncias/USAWestside2009.xml", "./USAWestside2009.lp")
