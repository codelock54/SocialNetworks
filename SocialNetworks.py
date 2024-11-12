import networkx as nx
import matplotlib.pyplot as plt
from neo4j import GraphDatabase
from collections import deque
import string
import os


class SocialNetwork:
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_friend(self, person1, person2):
        """
        Agrega una relación de amistad entre dos personas en la base de datos.

        Esta función invoca una transacción para crear los nodos de las personas
        si no existen y crear una relación bidireccional de amistad.

        Complejidad Temporal:
        - O(1) para ejecutar las consultas a Neo4j.
        - Si los nodos ya existen, el tiempo de ejecución será constante.

        Complejidad Espacial:
        - O(1) para almacenar las consultas en memoria.
        - O(n) en el peor caso si los nodos necesitan ser creados o si hay que almacenar
          un gran número de relaciones.
        """
        with self.driver.session() as session:
            session.write_transaction(self._add_friend_transaction, person1, person2)

    @staticmethod
    def _add_friend_transaction(tx, person1, person2):
        """
        Transacción para agregar una relación de amistad en la base de datos.

        Esta transacción asegura que los nodos de las personas existan en la base de datos,
        y luego crea una relación de amistad bidireccional entre ellas.

        Complejidad Temporal:
        - O(1) para las operaciones de lectura y escritura, ya que solo se están buscando
          y creando nodos y relaciones de forma directa.

        Complejidad Espacial:
        - O(1) en términos de la memoria utilizada para ejecutar las consultas. Sin embargo,
          el almacenamiento real de los nodos y las relaciones está gestionado por Neo4j.
        """
        # Crear nodos si no existen
        tx.run("MERGE (a:Person {name: $person1})", person1=person1)
        tx.run("MERGE (b:Person {name: $person2})", person2=person2)

        # Crear relación de amistad bidireccional
        tx.run(
            """
            MATCH (a:Person {name: $person1}), (b:Person {name: $person2})
            MERGE (a)-[:FRIEND]->(b)
            MERGE (b)-[:FRIEND]->(a)
        """,
            person1=person1,
            person2=person2,
        )

    def find_friend_groups(self, use_dfs=True):
        """
        Encuentra el número de grupos de amigos (componentes conexas) en la red social.

        Utiliza DFS o BFS para explorar los grupos de amigos. La elección entre DFS y BFS
        se realiza mediante el parámetro `use_dfs`.

        Complejidad Temporal:
        - O(N + E), donde N es el número de nodos (personas) y E es el número de relaciones
        de amistad (aristas) en la red social. El tiempo depende de la cantidad de nodos
        y relaciones que se deben explorar.

        Complejidad Espacial:
        - O(N), ya que se necesita almacenar el conjunto de nodos visitados.

        Parámetros:
        - `use_dfs`: Booleano que determina si se utiliza DFS (True) o BFS (False).

        Retorna:
        - El número de grupos de amigos (componentes conexas).
        """
        with self.driver.session() as session:
            return session.read_transaction(
                self._find_friend_groups_transaction, use_dfs
            )

    @staticmethod
    def _find_friend_groups_transaction(tx, use_dfs):
        """
        Transacción para encontrar los grupos de amigos en la base de datos.

        Esta función se ejecuta en la base de datos de Neo4j para encontrar todos los grupos
        de amigos, ya sea usando DFS o BFS. Un grupo de amigos es un conjunto de personas
        que están todas conectadas entre sí directa o indirectamente.

        Complejidad Temporal:
        - O(N + E), donde N es el número de nodos (personas) y E es el número de relaciones
        de amistad. Esto es porque se deben explorar todos los nodos y sus relaciones.

        Complejidad Espacial:
        - O(N), ya que se necesita un conjunto para almacenar los nodos visitados.

        Parámetros:
        - `tx`: Transacción en la que se ejecutan las consultas.
        - `use_dfs`: Booleano que indica si se utiliza DFS (True) o BFS (False).

        Retorna:
        - El número de grupos de amigos encontrados.
        """
        visited = set()
        num_groups = 0

        # Obtener todos los nodos
        result = tx.run("MATCH (p:Person) RETURN p.name AS name")
        all_nodes = [record["name"] for record in result]

        for node in all_nodes:
            if node not in visited:
                num_groups += 1

                if use_dfs:
                    SocialNetwork._dfs(tx, node, visited)
                else:
                    SocialNetwork._bfs(tx, node, visited)

        return num_groups

    @staticmethod
    def _dfs(tx, node, visited):
        """
        Realiza una búsqueda en profundidad (DFS) para explorar los amigos de un nodo dado.

        La búsqueda en profundidad explora todos los amigos de manera recursiva.

        Complejidad Temporal:
        - O(N + E), ya que se exploran todos los nodos y aristas a los que están conectados.

        Complejidad Espacial:
        - O(N), ya que la pila de recursión puede crecer hasta el tamaño de la red social.

        Parámetros:
        - `tx`: Transacción para ejecutar la consulta.
        - `node`: Nodo inicial (persona) desde donde comienza la búsqueda.
        - `visited`: Conjunto de nodos que ya han sido visitados.
        """
        stack = [node]
        visited.add(node)

        while stack:
            current_node = stack.pop()

            # Explorar todos los vecinos
            result = tx.run(
                "MATCH (p:Person {name: $name})-[:FRIEND]->(f) RETURN f.name AS friend",
                name=current_node,
            )
            for record in result:
                neighbor = record["friend"]
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)

    @staticmethod
    def _bfs(tx, node, visited):
        """
        Realiza una búsqueda en amplitud (BFS) para explorar los amigos de un nodo dado.

        La búsqueda en amplitud explora los amigos nivel por nivel.

        Complejidad Temporal:
        - O(N + E), ya que se exploran todos los nodos y aristas a los que están conectados.

        Complejidad Espacial:
        - O(N), debido a que se necesita espacio para almacenar los nodos en la cola.

        Parámetros:
        - `tx`: Transacción para ejecutar la consulta.
        - `node`: Nodo inicial (persona) desde donde comienza la búsqueda.
        - `visited`: Conjunto de nodos que ya han sido visitados.
        """

        queue = deque([node])
        visited.add(node)

        while queue:
            current_node = queue.popleft()

            # Explorar todos los vecinos
            result = tx.run(
                "MATCH (p:Person {name: $name})-[:FRIEND]->(f) RETURN f.name AS friend",
                name=current_node,
            )
            for record in result:
                neighbor = record["friend"]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

    def recommend_friends(self):
        """
        Recomienda amigos para cada persona en la red social utilizando el concepto de amigos de amigos.

        Este método genera una lista de recomendaciones para cada persona, basada en los amigos de sus amigos
        que no sean ya amigos directos ni la persona misma.

        Complejidad Temporal:
        - O(N^2), Esto se debe a que, para cada persona, se obtiene la lista de sus amigos (O(N)), y luego para cada amigo, se obtienen los amigos de ese amigo (O(N)).

        Complejidad Espacial:
        - O(N²), ya que se necesita almacenar las recomendaciones de amigos para cada persona, y cada persona tiene como máximo N recomendaciones.

        Retorna:
        - Un diccionario con las recomendaciones de amigos para cada persona.
        """
        with self.driver.session() as session:
            return session.read_transaction(self._recommend_friends_transaction)

    @staticmethod
    def _recommend_friends_transaction(tx):
        """
        Transacción para recomendar amigos en la base de datos.

        Para cada persona, este método busca a sus amigos y a los amigos de sus amigos,
        excluyendo a las personas que ya son sus amigos directos.

        Parámetros:
        - `tx`: Transacción para ejecutar la consulta en la base de datos.

        Retorna:
        - Un diccionario con las recomendaciones de amigos para cada persona.
        """
        recommendations = {}

        # Obtener todas las personas
        result = tx.run("MATCH (p:Person) RETURN p.name AS person")
        people = [record["person"] for record in result]

        for person in people:
            recommendations[person] = []

            # Obtener amigos de la persona actual
            friends_result = tx.run(
                "MATCH (p:Person {name: $name})-[:FRIEND]->(f) RETURN f.name AS friend",
                name=person,
            )
            friends = {record["friend"] for record in friends_result}

            for friend in friends:
                # Obtener amigos del amigo
                friends_of_friend_result = tx.run(
                    "MATCH (f:Person {name: $friend})-[:FRIEND]->(fof) RETURN fof.name AS fof",
                    friend=friend,
                )
                friends_of_friend = {
                    record["fof"] for record in friends_of_friend_result
                }

                potential_friends = friends_of_friend - friends - {person}

                recommendations[person].extend(potential_friends)

            recommendations[person] = list(set(recommendations[person]))

        return recommendations

    def most_popular_friend(self):
        """
        Encuentra a las personas más populares en la red social, es decir, las que tienen más amigos.

        En caso de empate, retorna a todas las personas que tienen el mismo número máximo de amigos.

        Complejidad Temporal:
        - O(N), donde N es el número de personas en la red social. Se ejecuta una consulta que cuenta los amigos para cada persona.

        Complejidad Espacial:
        - O(N), ya que se almacena la lista de personas y el número de amigos en la consulta.

        Retorna:
        - Una lista de tuplas, cada una con el nombre de una persona y su número de amigos.
        """
        with self.driver.session() as session:
            return session.read_transaction(self._most_popular_friend_transaction)

    @staticmethod
    def _most_popular_friend_transaction(tx):
        """
        Transacción para encontrar a las personas más populares en la red social (con más amigos).

        Parámetros:
        - `tx`: Transacción para ejecutar la consulta en la base de datos.

        Retorna:
        - Una lista de tuplas (persona, num_friends) con todas las personas con el mismo número máximo de amigos.
        """
        # Encontrar el número máximo de amigos
        result = tx.run(
            """
            MATCH (p:Person)
            RETURN p.name AS person, SIZE([(p)-[:FRIEND]->(f:Person) | f]) AS num_friends
            """
        )

        # Recoger todos los resultados
        friends_count = [record for record in result]

        # Encontrar el número máximo de amigos
        if not friends_count:
            return []

        max_friends = max(friends_count, key=lambda x: x["num_friends"])["num_friends"]

        # Filtrar todas las personas que tienen el mismo número máximo de amigos
        popular_friends = [
            (record["person"], record["num_friends"])
            for record in friends_count
            if record["num_friends"] == max_friends
        ]

        return popular_friends

    def shortest_path(self, person1, person2):
        """
        Encuentra el camino más corto entre dos personas en la red de amigos.

        Utiliza la función `shortestPath` de Cypher para encontrar el camino más corto en términos de relaciones de amistad.

        Complejidad Temporal:
        - O(N + E), donde:
        - N es el número de personas en la red.
        - E es el número de relaciones de amistad (aristas) en la red.

        Complejidad Espacial:
        - O(N), ya que se almacenan los nodos en el camino más corto.

        Parámetros:
        - `person1`: El nombre de la primera persona.
        - `person2`: El nombre de la segunda persona.

        Retorna:
        - Una lista de nombres de personas en el camino más corto desde `person1` hasta `person2`, o `None` si no hay camino.
        """
        with self.driver.session() as session:
            return session.read_transaction(
                self._shortest_path_transaction, person1, person2
            )

    @staticmethod
    def _shortest_path_transaction(tx, person1, person2):
        """
        Transacción que busca el camino más corto entre dos personas en la base de datos usando BFS

        Utiliza la función `shortestPath` de Cypher para calcular el camino más corto entre `person1` y `person2`.

        Parámetros:
        - `tx`: Transacción para ejecutar la consulta en la base de datos.
        - `person1`: El nombre de la primera persona.
        - `person2`: El nombre de la segunda persona.

        Retorna:
        - Una lista de nombres de personas en el camino más corto desde `person1` hasta `person2`, o `None` si no hay camino.
        """
        visited = set()
        parent = (
            {}
        )  # Diccionario para rastrear los nodos padres (para reconstruir el camino)
        queue = deque([person1])  # Cola para BFS, inicializada con la persona de inicio

        visited.add(person1)

        # Realizar BFS
        while queue:
            current = queue.popleft()

            # Si encontramos a person2, reconstruimos el camino
            if current == person2:
                path = []
                while current in parent:
                    path.append(current)
                    current = parent[current]
                path.append(person1)
                return path[::-1]  # Invertir el camino para que empiece en person1

            # Obtener amigos del nodo actual
            result = tx.run(
                "MATCH (p:Person {name: $name})-[:FRIEND]->(f) RETURN f.name AS friend",
                name=current,
            )

            for record in result:
                friend = record["friend"]
                if friend not in visited:
                    visited.add(friend)
                    parent[friend] = current
                    queue.append(friend)

        return None

    def has_cycle(self):
        """
        Verifica si hay ciclos en la red de amigos utilizando DFS.

        Complejidad Temporal:
        - O(N + E), donde:
        - N es el número de personas en la red.
        - E es el número de relaciones de amistad (aristas) en la red.

        Complejidad Espacial:
        - O(N), ya que se utilizan estructuras de datos para rastrear nodos visitados y el camino actual.

        Retorna:
        - Un ciclo (lista de nodos) si se detecta, o `False` si no hay ciclos.
        """
        with self.driver.session() as session:
            return session.read_transaction(self._has_cycle_transaction)

    @staticmethod
    def _has_cycle_transaction(tx):
        """
        Transacción que utiliza DFS para detectar ciclos en la red de amigos.

        Parámetros:
        - `tx`: Transacción para ejecutar la consulta en la base de datos.

        Retorna:
        - Un ciclo (lista de nodos) si se detecta, o `False` si no hay ciclos.
        """
        visited = set()  # Conjunto de nodos visitados

        # Obtener todos los nodos en la red social
        result = tx.run("MATCH (p:Person) RETURN p.name AS person")

        # Realizamos DFS para cada persona en la red
        for record in result:
            person = record["person"]
            if person not in visited:
                # Inicializar la pila para el DFS y el conjunto de nodos en el camino actual
                stack = [(person, None)]  # (nodo actual, nodo padre)
                path = []  # Pila que rastrea el camino actual para detectar ciclos

                while stack:
                    current_node, parent = stack.pop()

                    if current_node in visited:
                        # Si encontramos un ciclo
                        if current_node in path:
                            cycle_start = path.index(current_node)
                            cycle = path[cycle_start:]
                            cycle.append(current_node)
                            return cycle
                        continue

                    visited.add(current_node)
                    path.append(current_node)

                    # Obtener los amigos (vecinos) del nodo actual
                    neighbors = tx.run(
                        "MATCH (p:Person {name: $name})-[:FRIEND]->(f) RETURN f.name AS friend",
                        name=current_node,
                    ).values()

                    for record in neighbors:
                        neighbor = record[0]
                        if neighbor != parent:  # Evitar regresar al nodo padre
                            if neighbor in visited and neighbor in path:
                                # Detectar el ciclo si el nodo está en `path`
                                cycle_start = path.index(neighbor)
                                cycle = path[cycle_start:]
                                cycle.append(neighbor)
                                return cycle
                            stack.append((neighbor, current_node))

                # Remover el nodo del camino actual si no se encontraron ciclos
                path.pop()

    def remove_friend(self, person1, person2):
        """
        Elimina la relación de amistad entre `person1` y `person2` en ambas direcciones.

        Parámetros:
        - person1 (str): Nombre de la primera persona.
        - person2 (str): Nombre de la segunda persona.

        Complejidad:
        La complejidad de este método es O(1) en términos de la operación de eliminación específica
        en una base de datos de grafos como Neo4j, ya que la operación DELETE en una relación específica
        no depende del tamaño de la red, sino únicamente de la existencia de la relación entre los nodos.
        """
        with self.driver.session() as session:
            session.write_transaction(self._remove_friend_transaction, person1, person2)

    @staticmethod
    def _remove_friend_transaction(tx, person1, person2):
        """
        Transacción para eliminar la relación de amistad entre `person1` y `person2` en ambas direcciones.
        """
        tx.run(
            "MATCH (a:Person {name: $person1})-[r:FRIEND]->(b:Person {name: $person2}) DELETE r",
            person1=person1,
            person2=person2,
        )
        tx.run(
            "MATCH (a:Person {name: $person2})-[r:FRIEND]->(b:Person {name: $person1}) DELETE r",
            person1=person1,
            person2=person2,
        )

    def plot_friends(self):
        """
        Plotea las relaciones entre amigos desde la base de datos utilizando NetworkX y Matplotlib.

        Pasos:
        - Recupera las relaciones de amistad entre nodos de la base de datos Neo4j.
        - Construye un grafo no dirigido con NetworkX.
        - Plotea el grafo mostrando las conexiones de amistad.

        Complejidad:
        - Consulta de la base de datos (MATCH): O(N), donde N es el número de relaciones de amistad.
        - Construcción del grafo en NetworkX: O(N), dado que cada relación se agrega como un borde.

        """
        with self.driver.session() as session:
            # Recuperar nodos y relaciones de la base de datos
            query = """
            MATCH (a:Person)-[:FRIEND]->(b:Person)
            RETURN a.name AS person, b.name AS friend
            """
            result = session.run(query)

            G = nx.Graph()

            for record in result:
                G.add_edge(record["person"], record["friend"])

            plt.figure(figsize=(10, 8))
            nx.draw(
                G,
                with_labels=True,
                node_color="lightblue",
                node_size=500,
                font_size=10,
                font_color="black",
                font_weight="bold",
                edge_color="#ccbd13",
            )

            plt.title("Grafo de Red Social", size=16)
            plt.show()

    def create_adList(self, filename="lista_adyacencia.txt"):
        """
        Genera una lista de adyacencia desde la base de datos Neo4j y la guarda en un archivo de texto.

        Parámetros:
        - filename (str): Nombre del archivo en el cual se guardará la lista de adyacencia.

        Funcionamiento:
        - Consulta los nodos en la base de datos y construye una lista de IDs.
        - Crea una lista de adyacencia que almacena las relaciones (amigos) de cada nodo.
        - Guarda la lista de adyacencia en un archivo de texto en formato legible.

        Complejidad:
        - La consulta de nodos es O(N), donde N es el número de nodos en la base de datos.
        - La consulta de relaciones es O(E), donde E es el número de relaciones en la base de datos.
        - El tiempo de construcción de la lista de adyacencia es O(E).
        - La escritura en archivo es O(N + E), ya que cada nodo y relación se almacena en el archivo.
        """
        with self.driver.session() as session:
            query = """
        MATCH (p:Person)-[:FRIEND]->(amigo:Person)
        RETURN p.name AS persona, collect(amigo.name) AS amigos
        """
            result = session.run(query)

            with open(filename, "w") as file:
                for record in result:
                    persona = record["persona"]
                    amigos = record["amigos"]
                    file.write(f"{persona}: {', '.join(amigos)}\n")

    def print_list(self):
        """
        Imprime la lista de adyacencia de la red social.

        Funcionamiento:
        - Itera sobre los nodos y, para cada nodo, muestra sus amigos en un formato legible.
        - Convierte los índices numéricos de los nodos en letras (A, B, C, etc.) para una representación más clara.

        Complejidad:
        - O(N + E), donde N es el número de nodos y E es el número de relaciones.
        - O(N) para iterar sobre los nodos.
        - O(E) para acceder a las listas de amigos de cada nodo.
        """
        with self.driver.session() as session:
            query = """
        MATCH (p:Person)-[:FRIEND]->(amigo:Person)
        RETURN p.name AS persona, collect(amigo.name) AS amigos
        """
            result = session.run(query)
            for record in result:
                persona = record["persona"]
                amigos = record["amigos"]
                print(f"Nodo {persona}: {', '.join(amigos)}")

    def read_adjacency_list_from_file(self, filepath):
        """
        Lee una lista de adyacencia desde un archivo y la convierte en un diccionario.

        Parámetros:
        - filepath (str): Ruta del archivo que contiene la lista de adyacencia.

        Funcionamiento:
        - Cada línea del archivo debe tener el formato: Nodo: Nodo1, Nodo2, ...
        - La función divide cada línea para extraer el nodo y sus nodos adyacentes, y los almacena en un diccionario.

        Retorno:
        - adjacency_list (dict): Diccionario donde cada clave es un nodo y su valor es una lista de nodos adyacentes.

        Complejidad:
        - O(N), donde N es el número de líneas en el archivo.
        """
        adjacency_list = {}
        with open(filepath, "r") as file:
            for line in file:
                parts = line.strip().split(":")
                if len(parts) == 2:
                    node = parts[0].strip()
                    edges = [edge.strip() for edge in parts[1].split(",")]
                    adjacency_list[node] = edges
        return adjacency_list


    def add_graph_to_neo4j(self, graph):
        """
            Añade un diccionario de tipo grafo a la base de datos Neo4j.
            
            Parámetros:
            - graph (dict): Un diccionario donde las claves son nodos (nombres de personas) y los valores son listas 
            de amigos asociados. Ejemplo: {'A': ['B', 'C'], 'B': ['A'], 'C': ['A']}.

            Pasos:
            1. Crea nodos de personas si no existen, utilizando el comando MERGE de Neo4j.
            2. Crea relaciones de amistad entre nodos.
            
            Complejidad:
            - Creación de nodos (MERGE): O(N), donde N es el número de nodos en el grafo. Cada nodo se añade o verifica solo una vez.
            - Creación de relaciones (MERGE para cada relación): O(E), donde E es el número de aristas en el grafo. 
            La complejidad total es O(N + E), 
        """
        with self.driver.session() as session:
            for node in graph:
                session.run("MERGE (n:Person {name: $name})", name=node)

            for node, friends in graph.items():
                for friend in friends:
                    session.run(
                        """
                        MATCH (a:Person {name: $node}), (b:Person {name: $friend})
                        MERGE (a)-[:FRIEND]->(b)
                    """,
                        node=node,
                        friend=friend,
                    )

    def delete_account(self, nombres_nodos):
        """
        Elimina uno o más nodos de la base de datos de Neo4j en función de los nombres proporcionados.
        
        Args:
            nombres_nodos (list): Lista de nombres de nodos a eliminar.
        """
        with self.driver.session() as session:
            if isinstance(nombres_nodos, str):
                nombres_nodos = [nombres_nodos]  

            for nombre in nombres_nodos:
                session.run("""
                    MATCH (n {name: $nombre})
                    DETACH DELETE n
                    """, nombre=nombre)
        print(f"Nodos {', '.join(nombres_nodos)} eliminados de la base de datos.")


    def all_accounts(self):
        """
        Recupera todos los nombres de los nodos en la base de datos Neo4j.

        Este método ejecuta una consulta Cypher que encuentra todos los nodos en la base de datos
        y devuelve una lista de sus nombres. Si un nodo no tiene la propiedad `name`, ese nodo
        no se incluirá en el resultado.

        Returns:
            list: Una lista de strings que representa los nombres de todos los nodos
            presentes en la base de datos.

        """
        with self.driver.session() as session:
            query = "MATCH (n) RETURN n.name AS nombre"
            result = session.run(query)
            # Recopilamos todos los nombres de nodos en una lista
            nodos = [record["nombre"] for record in result]
        return nodos
