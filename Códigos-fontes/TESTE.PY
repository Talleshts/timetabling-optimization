import xml.etree.ElementTree as ET

def parse_and_generate_lp(xml_file, lp_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Erro ao ler o arquivo XML: {e}")
        return

    times = []
    rooms = []
    events = []

    # Parse Times
    for time in root.findall(".//Time"):
        time_id = time.attrib.get("Id")
        if time_id:
            times.append(time_id)

    # Parse Rooms
    for room in root.findall(".//Resource"):
        resource_type = room.find("ResourceType")
        if resource_type is not None and resource_type.attrib.get("Reference") == "Room":
            room_id = room.attrib.get("Id")
            if room_id:
                rooms.append(room_id)

    # Parse Events
    for event in root.findall(".//Event"):
        event_id = event.attrib.get("Id")
        if not event_id:
            continue  # Skip events without an ID

        # Extract Class and Teacher
        class_resource = event.find(".//Resource[Role='Class']")
        teacher_resource = event.find(".//Resource[Role='Teacher']")
        
        if class_resource is None or teacher_resource is None:
            print(f"Aviso: Evento {event_id} ignorado. Classe ou professor ausentes.")
            continue

        class_id = class_resource.attrib.get("Reference")
        teacher_id = teacher_resource.attrib.get("Reference")

        if not class_id or not teacher_id:
            print(f"Aviso: Evento {event_id} ignorado. Referência de classe ou professor ausente.")
            continue

        # Extract Duration
        duration_elem = event.find("Duration")
        duration = int(duration_elem.text) if duration_elem is not None else 1

        events.append({
            "id": event_id,
            "class": class_id,
            "teacher": teacher_id,
            "duration": duration,
        })

    # Check if essential data exists
    if not times:
        print("Erro: Nenhum elemento <Time> válido foi encontrado.")
        return
    if not rooms:
        print("Erro: Nenhum elemento <Room> válido foi encontrado.")
        return
    if not events:
        print("Erro: Nenhum evento válido foi encontrado.")
        return

    # Generate LP File
    with open(lp_file, "w") as f:
        f.write("Minimize\n")
        f.write(" obj: ")

        # Objective function
        obj_terms = [f"1 x_{event['teacher']}_{event['class']}_{time}_{room}" 
                     for event in events for time in times for room in rooms]
        f.write(" + ".join(obj_terms) + "\n")

        f.write("Subject To\n")

        # Constraint: Each event occurs once
        for event in events:
            terms = [f"x_{event['teacher']}_{event['class']}_{time}_{room}" 
                     for time in times for room in rooms]
            f.write(f" event_{event['id']}: " + " + ".join(terms) + " = 1\n")

        # Constraint: No room is used more than once at the same time
        for time in times:
            for room in rooms:
                terms = [f"x_{event['teacher']}_{event['class']}_{time}_{room}" 
                         for event in events]
                f.write(f" room_{room}_{time}: " + " + ".join(terms) + " <= 1\n")

        # Constraint: No teacher is double-booked
        for teacher in set(event['teacher'] for event in events):
            for time in times:
                terms = [f"x_{teacher}_{event['class']}_{time}_{room}" 
                         for event in events if event['teacher'] == teacher for room in rooms]
                f.write(f" teacher_{teacher}_{time}: " + " + ".join(terms) + " <= 1\n")

        f.write("Binary\n")
        for event in events:
            for time in times:
                for room in rooms:
                    f.write(f" x_{event['teacher']}_{event['class']}_{time}_{room}\n")

        f.write("End\n")

# Execute the function
parse_and_generate_lp("./Instâncias/ArtificialSudoku4x4.xml", "./outputs/lps/ArtificialSudoku4x4.lp")
