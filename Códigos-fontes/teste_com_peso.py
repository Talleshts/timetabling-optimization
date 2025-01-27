import xml.etree.ElementTree as ET

def read_xml_and_generate_lp_with_weights(input_file, output_file):
    tree = ET.parse(input_file)
    root = tree.getroot()

    # Dicionários para armazenar os dados
    times = []
    rooms = []
    events = []

    print("Lendo os tempos...")
    for time in root.findall(".//Time"):
        ref = time.attrib.get("Reference")
        if ref:
            times.append(ref)

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
        objective_terms = []

        for event in events:
            teacher = event['teacher']
            class_group = event['class']
            for time in times:
                var = f"x_{event['id']}_{time}"
                objective_terms.append(f"3 {var}")  # ω = 3 para períodos ociosos
            objective_terms.append(f"9 y_{teacher}")  # γ = 9 para dias de trabalho
            objective_terms.append(f"1 z_{event['id']}")  # δ = 1 para aulas duplas não satisfeitas

        lp_file.write(" + ".join(objective_terms) + "\n")
        lp_file.write("Subject To\n")

        # Restrições: cada evento deve ocorrer em apenas um timeslot
        for event in events:
            lp_file.write(f"""  {' + '.join([f'x_{event["id"]}_{time}' for time in times])} = {event['duration']}\n""")

        # Restrições de sala: uma sala só pode ser usada por um evento por vez
        for time in times:
            for room in rooms:
                lp_file.write(f"""  {' + '.join([f'x_{event["id"]}_{time}' for event in events])} <= 1\n""")

        lp_file.write("Binary\n")
        for event in events:
            for time in times:
                lp_file.write(f"  x_{event['id']}_{time}\n")
            lp_file.write(f"  y_{event['teacher']}\n")
            lp_file.write(f"  z_{event['id']}\n")

        lp_file.write("End\n")

    print(f"Arquivo LP gerado em {output_file}")

# Exemplo de chamada da função
read_xml_and_generate_lp_with_weights("./Instâncias/ArtificialSudoku4x4.xml", "./outputs/lps/ArtificialSudoku4x4.lp")