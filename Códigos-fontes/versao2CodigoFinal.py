import xml.etree.ElementTree as ET

def read_xml_and_generate_lp_with_weights(input_file, output_file):
    tree = ET.parse(input_file)
    root = tree.getroot()

    # Encontrar a tag <Instances>
    instances = root.find(".//Instances")
    if instances is None:
        print("Erro: Nenhuma tag <Instances> encontrada.")
        return

    # Dicionários para armazenar os dados
    times = []
    events = []
    time_groups = {}

    print("Lendo os tempos...")
    for time in instances.findall(".//Time"):
        time_id = time.attrib.get("Id")
        ref = time.find(".//Day").attrib.get("Reference") if time.find(".//Day") is not None else None
        if time_id and ref:
            times.append({"id": time_id, "group": ref})
    print(f"Tempos lidos: {times}")

    print("Lendo os grupos de tempo...")
    for group in instances.findall(".//TimeGroups/*"):
        ref = group.attrib.get("Id")
        name_elem = group.find("Name")
        name = name_elem.text if name_elem is not None else ref
        if ref and name:
            time_groups[ref] = name
    print(f"Grupos de tempo lidos: {time_groups}")

    print("Lendo os eventos...")
    for idx, event in enumerate(instances.findall(".//Event"), start=1):
        event_id = f"E{idx}"  # Abreviação numérica para o ID do evento
        duration_elem = event.find("Duration")
        if duration_elem is not None and duration_elem.text.isdigit():
            duration = int(duration_elem.text)
        else:
            print(f"Aviso: Evento {event_id} ignorado. Duração ausente ou inválida.")
            continue

        resources = [res.attrib.get("Reference") for res in event.findall(".//Resource")]
        print(f"Recursos do evento {event_id}: {resources}")
        teacher = next((res for res in resources if res.startswith("T")), None)
        class_group = next((res for res in resources if res.startswith("S")), None)
        print(f"Professor: {teacher}, Classe: {class_group}")

        if not teacher:
            print(f"Aviso: Evento {event_id} ignorado. Professor ausente.")
        if not class_group:
            print(f"Aviso: Evento {event_id} ignorado. Classe ausente.")

        if teacher and class_group:
            events.append({
                "id": event_id,
                "duration": duration,
                "teacher": teacher,
                "class": class_group
            })
    print(f"Eventos lidos: {events}")

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

        # Restrição 2: Conservação de Fluxo
        for teacher in {e["teacher"] for e in events if e["teacher"]}:
            for time in times:
                terms_in = [f"x_{teacher}_{event['class']}_{time['id']}" for event in events if event["teacher"] == teacher and event["class"]]
                terms_out = [f"x_{teacher}_{event['class']}_{time['id']}" for event in events if event["teacher"] == teacher and event["class"]]
                
                # Determinar o valor de b_v
                # PERGUNTAR GERALDO SOBRE ESSE PONTO
                if time["id"].endswith("_1"):  # Supondo que o primeiro período do dia seja a origem
                    b_v = 1
                elif time["id"].endswith("_5"):  # Supondo que o último período do dia seja o destino
                    b_v = -1
                else:
                    b_v = 0
                
                if terms_in or terms_out:
                    constraint_name = f"flow_{teacher}_{time['id']}"
                    lp_file.write(f" {constraint_name}: " + " + ".join(terms_in) + " - " + " - ".join(terms_out) + f" = {b_v}\n")

        # Restrição 3: Capacidade unitária dos arcos de aula
        for cls in {e["class"] for e in events if e["class"]}:
            for time in times:
                terms = [f"x_{event['teacher']}_{cls}_{time['id']}" for event in events if event["class"] == cls and event["teacher"]]
                if terms:
                    constraint_name = f"capacity_{cls}_{time['id']}"
                    lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " <= 1\n")

        # Restrição 4: Número de aulas obrigatórias
        for event in events:
            if event["teacher"] and event["class"]:
                terms = [f"x_{event['teacher']}_{event['class']}_{time['id']}" for time in times]
                if terms:
                    constraint_name = f"workload_{event['teacher']}_{event['class']}"
                    lp_file.write(f" {constraint_name}: " + " + ".join(terms) + f" = {event['duration']}\n")

        # Restrição 5: Máximo de aulas diárias
        for event in events:
            if event["teacher"] and event["class"]:
                daily_terms = {}
                for time in times:
                    group = time_groups.get(time["group"], time["group"])
                    if group not in daily_terms:
                        daily_terms[group] = []
                    daily_terms[group].append(f"x_{event['teacher']}_{event['class']}_{time['id']}")
                for group, terms in daily_terms.items():
                    if terms:
                        constraint_name = f"max_daily_{event['teacher']}_{event['class']}_{group}"
                        lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " <= 2\n")

        # Restrição 6: Aulas no primeiro período do dia
        for cls in {e["class"] for e in events if e["class"]}:
            for time in times:
                if time["id"].endswith("_1"):  # Primeiro período do dia
                    terms = [f"x_{event['teacher']}_{cls}_{time['id']}" for event in events if event["class"] == cls and event["teacher"]]
                    if terms:
                        constraint_name = f"first_period_{cls}_{time['id']}"
                        lp_file.write(f" {constraint_name}: " + " + ".join(terms) + " <= 1\n")

        # Restrição 7: Aulas duplas não atendidas
        for event in events:
            if event["teacher"] and event["class"]:
                for i, time in enumerate(times[:-1]):
                    current_time = time["id"]
                    next_time = times[i + 1]["id"]
                    if time["group"] == times[i + 1]["group"]:
                        double_var = f"double_{event['id']}_{current_time}"
                        terms = [
                            f"x_{event['teacher']}_{event['class']}_{current_time}",
                            f"x_{event['teacher']}_{event['class']}_{next_time}"
                        ]
                        if terms:
                            constraint_name = f"double_lessons_{event['teacher']}_{event['class']}_{current_time}"
                            lp_file.write(f" {constraint_name}: " + double_var + " - " + " - ".join(terms) + " >= -1\n")

        # Restrição 8: Mínimo de dias de trabalho
        for teacher in {e["teacher"] for e in events if e["teacher"]}:
            for group in time_groups.values():
                terms = [f"x_{teacher}_{time['id']}" for time in times if time_groups.get(time["group"], time["group"]) == group]
                if terms:
                    constraint_name = f"working_days_{teacher}_{group}"
                    lp_file.write(f" {constraint_name}: " + f"days_{teacher}" + " - " + " - ".join(terms) + " >= 0\n")

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
read_xml_and_generate_lp_with_weights("Instâncias/BrazilInstance2.xml", "./outputs/lps/BrazilInstance2.lp")