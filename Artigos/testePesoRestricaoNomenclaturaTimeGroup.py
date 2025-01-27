import xml.etree.ElementTree as ET

def read_xml_and_generate_lp_with_weights(input_file, output_file):
    tree = ET.parse(input_file)
    root = tree.getroot()

    # Dicionários para armazenar os dados
    times = []
    rooms = []
    events = []
    resources = []
    constraints = []
    time_groups = {}

    print("Lendo os tempos...")
    for time in root.findall(".//Time"):
        time_id = time.attrib.get("Id")
        ref = time.find(".//Day").attrib.get("Reference") if time.find(".//Day") is not None else None
        if time_id and ref:
            times.append({"id": time_id, "group": ref})

    print("Lendo os grupos de tempo...")
    for group in root.findall(".//TimeGroups/*"):
        ref = group.attrib.get("Id")
        name = group.find("Name").text
        if ref and name:
            time_groups[ref] = name

    print("Lendo as salas...")
    for resource in root.findall(".//Resource"):
        res_type = resource.find("ResourceType")
        if res_type is not None and res_type.attrib.get("Reference") == "Room":
            rooms.append(resource.attrib.get("Reference"))

    print("Lendo os eventos...")
    for idx, event in enumerate(root.findall(".//Event"), start=1):
        if event.tag == "Instances":
            break
        event_id = f"E{idx}"  # Abreviação numérica para o ID do evento
        duration_elem = event.find("Duration")
        if duration_elem is not None and duration_elem.text.isdigit():
            duration = int(duration_elem.text)
        else:
            print(f"Aviso: Evento {event_id} ignorado. Duração ausente ou inválida.")
            continue

        resources = [res.attrib.get("Reference") for res in event.findall(".//Resource")]
        teacher = next((res for res in resources if "T" in res), None)
        class_group = next((res for res in resources if "C" in res), None)

        if teacher and class_group:
            events.append({
                "id": event_id,
                "duration": duration,
                "teacher": teacher,
                "class": class_group
            })
        else:
            print(f"Aviso: Evento {event_id} ignorado. Classe ou professor ausentes.")

    if not rooms:
        print("Erro: Nenhum elemento <Room> válido foi encontrado.")
        return

    print("Gerando arquivo LP...")
    with open(output_file, "w") as lp_file:
        lp_file.write("Minimize\n")
        objective_terms = set()

        for event in events:
            teacher = event['teacher']
            class_group = event['class']
            for time in times:
                var = f"x_{teacher}_{class_group}_{time['id']}"
                objective_terms.add(f"3 {var}")  # ω = 3 para períodos ociosos
            objective_terms.add(f"9 y_{teacher}")  # γ = 9 para dias de trabalho
            objective_terms.add(f"1 g_{teacher}_{class_group}")  # δ = 1 para aulas duplas não satisfeitas

        lp_file.write(" + ".join(objective_terms) + "\n")
        lp_file.write("Subject To\n")

        # Restrições: cada evento deve ocorrer em apenas um timeslot
        for event in events:
            constraint_name = f"event_{event['id']}_timeslot"
            lp_file.write(f""" {constraint_name}: {' + '.join([f'x_{event["teacher"]}_{event["class"]}_{time["id"]}' for time in times])} = {event['duration']}\n""")

        # Restrições de sala: uma sala só pode ser usada por um evento por vez
        for time in times:
            for room in rooms:
                if room:
                    constraint_name = f"room_{room}_time_{time['id']}"
                    lp_file.write(f""" {constraint_name}: {' + '.join([f'x_{event["teacher"]}_{event["class"]}_{time["id"]}' for event in events])} <= 1\n""")

        # H1: Carga horária
        for event in events:
            if event["teacher"] and event["class"]:
                terms = [f"x_{event['teacher']}_{event['class']}_{time['id']}" for time in times]
                if terms:  # Verifica se há termos na restrição
                    constraint_name = f"H1_{event['teacher']}_{event['class']}"
                    lp_file.write(f" {constraint_name}: " + " + ".join(terms) + f" = {event['duration']}\n")

        # H2: Conflito de horário por professor
        for teacher in {e["teacher"] for e in events if e["teacher"]}:
            for time in times:
                terms = [f"x_{teacher}_{event['class']}_{time['id']}" for event in events if event["teacher"] == teacher and event["class"]]
                if terms:
                    constraint_name = f"H2_{teacher}_time_{time['id']}"
                    lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " <= 1\n")

        # H3: Conflito de horário por turma
        for cls in {e["class"] for e in events if e["class"]}:
            for time in times:
                terms = [f"x_{event['teacher']}_{cls}_{time['id']}" for event in events if event["class"] == cls and event["teacher"]]
                if terms:
                    constraint_name = f"H3_{cls}_time_{time['id']}"
                    lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " <= 1\n")

        # H4: Indisponibilidade dos professores
        for constraint in constraints:
            if constraint["name"] == "AvoidUnavailableTimes":
                for time in times:
                    terms = [f"x_{constraint['id']}_{event['class']}_{time['id']}" for event in events if event["teacher"] == constraint["id"] and event["class"]]
                    if terms:
                        constraint_name = f"H4_{constraint['id']}_time_{time['id']}"
                        lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " = 0\n")

        # H5: Máximo de aulas diárias
        for event in events:
            if event["teacher"] and event["class"] and event.get("max_daily"):
                daily_terms = {}
                for time in times:
                    group = time_groups.get(time["group"], time["group"])  # Usar o nome do grupo se disponível, caso contrário, usar o ID
                    if group not in daily_terms:
                        daily_terms[group] = []
                    daily_terms[group].append(f"x_{event['teacher']}_{event['class']}_{time['id']}")
                for group, terms in daily_terms.items():
                    if terms:
                        constraint_name = f"H5_{event['teacher']}_{event['class']}_group_{group}"
                        lp_file.write(f" {constraint_name}: " + " + ".join(terms) + f" <= {event['max_daily']}\n")

        # H6: Lições duplas
        for event in events:
            if event["teacher"] and event["class"] and event.get("double_lessons"):
                for i, time in enumerate(times[:-1]):
                    current_time = time["id"]
                    next_time = times[i + 1]["id"]
                    if time["group"] == times[i + 1]["group"]:  # Verificar se estão no mesmo grupo
                        double_var = f"double_{event['id']}_{current_time}"
                        terms = [
                            f"x_{event['teacher']}_{event['class']}_{current_time}",
                            f"x_{event['teacher']}_{event['class']}_{next_time}"
                        ]
                        if terms:
                            constraint_name = f"H6_{event['teacher']}_{event['class']}_time_{current_time}"
                            lp_file.write(f" {constraint_name}: " + double_var + " - " + " - ".join(terms) + " >= -1\n")

        # S1: Períodos ociosos
        for teacher in {e["teacher"] for e in events if e["teacher"]}:
            for group in time_groups.values():
                group_periods = [time for time in times if time_groups.get(time["group"], time["group"]) == group]
                for i in range(len(group_periods) - 1):
                    current = group_periods[i]["id"]
                    next_period = group_periods[i + 1]["id"]
                    idle_var = f"idle_{teacher}_{current}"
                    terms = []
                    for event in events:
                        if event["teacher"] == teacher:
                            terms.append(f"x_{teacher}_{event['class']}_{current}")
                            terms.append(f"x_{teacher}_{event['class']}_{next_period}")
                    if terms:
                        constraint_name = f"S1_{teacher}_time_{current}"
                        lp_file.write(f" {constraint_name}: " + idle_var + " - " + " - ".join(terms) + " >= 0\n")

        # S2: Dias de trabalho
        for teacher in {e["teacher"] for e in events if e["teacher"]}:
            for group in time_groups.values():
                terms = [f"x_{teacher}_{time['id']}" for time in times if time_groups.get(time["group"], time["group"]) == group]
                if terms:
                    constraint_name = f"S2_{teacher}_group_{group}"
                    lp_file.write(f" {constraint_name}: " + f"days_{teacher}" + " - " + " - ".join(terms) + " >= 0\n")

        # S3: Lições duplas solicitadas
        for event in events:
            if event.get("double_lessons"):
                terms = [f"double_{event['id']}_{time['id']}" for time in times]
                if terms:
                    constraint_name = f"S3_{event['teacher']}_{event['class']}"
                    lp_file.write(f" {constraint_name}: " + " + ".join(terms) + f" >= {event['double_lessons']}\n")

        lp_file.write("Binary\n")
        binary_vars = set()
        for event in events:
            for time in times:
                binary_vars.add(f"x_{event['teacher']}_{event['class']}_{time['id']}")
            binary_vars.add(f"y_{event['teacher']}")
            binary_vars.add(f"g_{event['teacher']}_{event['class']}")
        for var in binary_vars:
            lp_file.write(f"  {var}\n")

        lp_file.write("End\n")

    print(f"Arquivo LP gerado em {output_file}")

# Exemplo de chamada da função
read_xml_and_generate_lp_with_weights("./Instâncias\ArtificialAbramson15.xml", "./outputs/lps/AAAAAAAAAAAA.lp")