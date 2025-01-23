#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libxml/parser.h>
#include <libxml/tree.h>

// Estruturas para armazenar os dados
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
    char resource_class[50];
    char resource_teacher[50];
} Event;

// Funções para processar o XML
void parseTimes(xmlNode *node, Time times[], int *time_count) {
    for (xmlNode *cur_node = node; cur_node; cur_node = cur_node->next) {
        if (cur_node->type == XML_ELEMENT_NODE && strcmp((char *)cur_node->name, "Time") == 0) {
            strcpy(times[*time_count].id, (char *)xmlGetProp(cur_node, (const xmlChar *)"Id"));
            xmlNode *name_node = cur_node->children;
            while (name_node && strcmp((char *)name_node->name, "Name") != 0) {
                name_node = name_node->next;
            }
            if (name_node) {
                strcpy(times[*time_count].name, (char *)xmlNodeGetContent(name_node));
            }
            (*time_count)++;
        }
    }
}

void parseResources(xmlNode *node, Resource resources[], int *resource_count) {
    for (xmlNode *cur_node = node; cur_node; cur_node = cur_node->next) {
        if (cur_node->type == XML_ELEMENT_NODE && strcmp((char *)cur_node->name, "Resource") == 0) {
            strcpy(resources[*resource_count].id, (char *)xmlGetProp(cur_node, (const xmlChar *)"Id"));
            xmlNode *name_node = cur_node->children;
            while (name_node && strcmp((char *)name_node->name, "Name") != 0) {
                name_node = name_node->next;
            }
            if (name_node) {
                strcpy(resources[*resource_count].name, (char *)xmlNodeGetContent(name_node));
            }
            strcpy(resources[*resource_count].type, (char *)xmlGetProp(cur_node->children, (const xmlChar *)"Reference"));
            (*resource_count)++;
        }
    }
}

void parseEvents(xmlNode *node, Event events[], int *event_count) {
    for (xmlNode *cur_node = node; cur_node; cur_node = cur_node->next) {
        if (cur_node->type == XML_ELEMENT_NODE && strcmp((char *)cur_node->name, "Event") == 0) {
            strcpy(events[*event_count].id, (char *)xmlGetProp(cur_node, (const xmlChar *)"Id"));
            xmlNode *child = cur_node->children;
            while (child) {
                if (strcmp((char *)child->name, "Name") == 0) {
                    strcpy(events[*event_count].name, (char *)xmlNodeGetContent(child));
                } else if (strcmp((char *)child->name, "Duration") == 0) {
                    events[*event_count].duration = atoi((char *)xmlNodeGetContent(child));
                } else if (strcmp((char *)child->name, "Resources") == 0) {
                    xmlNode *res_node = child->children;
                    while (res_node) {
                        if (strcmp((char *)res_node->name, "Resource") == 0) {
                            char *role = (char *)xmlGetProp(res_node, (const xmlChar *)"Role");
                            if (strcmp(role, "Class") == 0) {
                                strcpy(events[*event_count].resource_class, (char *)xmlGetProp(res_node, (const xmlChar *)"Reference"));
                            } else if (strcmp(role, "Teacher") == 0) {
                                strcpy(events[*event_count].resource_teacher, (char *)xmlGetProp(res_node, (const xmlChar *)"Reference"));
                            }
                        }
                        res_node = res_node->next;
                    }
                }
                child = child->next;
            }
            (*event_count)++;
        }
    }
}

int main() {
    xmlDoc *doc = NULL;
    xmlNode *root_element = NULL;

    // Inicializar contadores e arrays
    Time times[100];
    Resource resources[100];
    Event events[100];
    int time_count = 0, resource_count = 0, event_count = 0;

    // Abrir o arquivo XML
    doc = xmlReadFile("BrazilInstance1.xml", NULL, 0);
    if (doc == NULL) {
        printf("Erro ao abrir o arquivo XML.\n");
        return -1;
    }

    // Obter o elemento raiz
    root_element = xmlDocGetRootElement(doc);

    // Processar o XML
    parseTimes(root_element->children, times, &time_count);
    parseResources(root_element->children, resources, &resource_count);
    parseEvents(root_element->children, events, &event_count);

    // Exemplo de saída
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
               events[i].id, events[i].name, events[i].duration, events[i].resource_class, events[i].resource_teacher);
    }

    // Liberar a memória
    xmlFreeDoc(doc);
    xmlCleanupParser();
    return 0;
}
