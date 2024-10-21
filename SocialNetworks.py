import networkx as nx
import matplotlib.pyplot as plt
from neo4j import GraphDatabase
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
        with self.driver.session() as session:
            session.write_transaction(self._add_friend_transaction, person1, person2)

    @staticmethod
    def _add_friend_transaction(tx, person1, person2):
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
        with self.driver.session() as session:
            return session.read_transaction(
                self._find_friend_groups_transaction, use_dfs
            )

    @staticmethod
    def _find_friend_groups_transaction(tx, use_dfs):
        visited = set()
        num_groups = 0

        # Obtener todos los nodos
        result = tx.run("MATCH (p:Person) RETURN p.name AS name")
        all_nodes = [record["name"] for record in result]

        # Loop a través de todos los nodos en el grafo
        for node in all_nodes:
            if node not in visited:
                # Encontrar un nuevo grupo, incrementar el contador
                num_groups += 1

                # Realizar DFS o BFS según el flag
                if use_dfs:
                    SocialNetwork._dfs(tx, node, visited)
                else:
                    SocialNetwork._bfs(tx, node, visited)

        return num_groups

    @staticmethod
    def _dfs(tx, node, visited):
        stack = [node]  # Inicializar stack para DFS
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
        from collections import deque

        queue = deque([node])  # Inicializar cola para BFS
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
        with self.driver.session() as session:
            return session.read_transaction(self._recommend_friends_transaction)

    @staticmethod
    def _recommend_friends_transaction(tx):
        recommendations = {}

        # Obtener todas las personas
        result = tx.run("MATCH (p:Person) RETURN p.name AS person")
        people = [record["person"] for record in result]

        for person in people:
            # Inicializamos la lista de recomendaciones para la persona
            recommendations[person] = []

            # Obtener amigos de la persona actual
            friends_result = tx.run(
                "MATCH (p:Person {name: $name})-[:FRIEND]->(f) RETURN f.name AS friend",
                name=person,
            )
            friends = {record["friend"] for record in friends_result}

            # Recorremos los amigos de la persona
            for friend in friends:
                # Obtener amigos del amigo
                friends_of_friend_result = tx.run(
                    "MATCH (f:Person {name: $friend})-[:FRIEND]->(fof) RETURN fof.name AS fof",
                    friend=friend,
                )
                friends_of_friend = {
                    record["fof"] for record in friends_of_friend_result
                }

                # Encontrar amigos en común que no sean la persona actual ni su amigo
                potential_friends = friends_of_friend - friends - {person}

                # Agregar las recomendaciones
                recommendations[person].extend(potential_friends)

            # Eliminar duplicados en las recomendaciones
            recommendations[person] = list(set(recommendations[person]))

        return recommendations

    def most_popular_friend(self):
        with self.driver.session() as session:
            return session.read_transaction(self._most_popular_friend_transaction)

    @staticmethod
    def _most_popular_friend_transaction(tx):
        result = tx.run(
            """
            MATCH (p:Person)
            RETURN p.name AS person, SIZE([(p)-[:FRIEND]->(f:Person) | f]) AS num_friends
            ORDER BY num_friends DESC
            LIMIT 1
            """
        )

        record = result.single()
        if record:
            return record["person"], record["num_friends"]
        return None, 0

    def shortest_path(self, person1, person2):
        with self.driver.session() as session:
            return session.read_transaction(
                self._shortest_path_transaction, person1, person2
            )

    @staticmethod
    def _shortest_path_transaction(tx, person1, person2):
        try:
            result = tx.run(
                "MATCH p=shortestPath((a:Person {name: $person1})-[:FRIEND*]->(b:Person {name: $person2})) RETURN [node IN nodes(p) | node.name] AS path",
                person1=person1,
                person2=person2,
            )
            record = result.single()
            return record["path"] if record else None
        except Exception as e:
            return None

    def has_cycle(self):
        with self.driver.session() as session:
            return session.read_transaction(self._has_cycle_transaction)

    @staticmethod
    def _has_cycle_transaction(tx):
        result = tx.run("MATCH (n) -[*]-> (n) RETURN COUNT(*) > 0 AS has_cycle")
        record = result.single()
        return record["has_cycle"] if record else False

    def remove_friend(self, person1, person2):
        with self.driver.session() as session:
            session.write_transaction(self._remove_friend_transaction, person1, person2)

    @staticmethod
    def _remove_friend_transaction(tx, person1, person2):
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
        with self.driver.session() as session:
            # Recuperar nodos y relaciones de la base de datos
            query = """
            MATCH (a:Person)-[:FRIEND]->(b:Person)
            RETURN a.name AS person, b.name AS friend
            """
            result = session.run(query)

            # Crear un grafo
            G = nx.Graph()

            # Añadir los nodos y las aristas del resultado
            for record in result:
                G.add_edge(record["person"], record["friend"])

            # Dibujar el grafo
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

            # Mostrar el gráfico
            plt.title("Grafo de Red Social", size=16)
            plt.show()

    # Función para agregar nodos y relaciones del grafo a Neo4j
    def add_graph_to_neo4j(self, graph):
        with self.driver.session() as session:
            # Primero creamos los nodos
            for node in graph:
                session.run("MERGE (n:Person {name: $name})", name=node)

            # Luego, creamos las relaciones entre los nodos
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

    def crearte_adList(self, filename="lista_adyacencia.txt"):
        with self.driver.session() as session:
            # Obtener todos los nodos
            nodos = session.run("MATCH (n) RETURN id(n) AS id")
            self.V = [record["id"] for record in nodos]

            # Inicializar lista de adyacencia
            self.L = [[] for _ in range(len(self.V))]

            # Obtener relaciones
            relaciones = session.run(
                "MATCH (a)-[:FRIEND]->(b) RETURN id(a) AS a, id(b) AS b"
            )

            for record in relaciones:
                a = record["a"]
                b = record["b"]
                self.L[a].append(b)  # Agregar b a la lista de adyacencia de a

            # Exportar a archivo .txt
            with open(filename, "w") as file:
                for i in range(len(self.V)):
                    # Convertir el índice a una letra
                    letra = string.ascii_uppercase[i]
                    # Convertir los índices de la lista de adyacencia a letras
                    amigos = [string.ascii_uppercase[j] for j in self.L[i]]
                    file.write(f"{letra}: {', '.join(amigos)}\n")

    def print_list(self):
        for i in range(len(self.V)):
            letra = string.ascii_uppercase[i]
            amigos = [string.ascii_uppercase[j] for j in self.L[i]]
            print(f"Nodo {letra}: {', '.join(amigos)}")
