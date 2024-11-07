# Social Network App

Este proyecto es una aplicación de red social que utiliza Neo4j como base de datos para gestionar relaciones de amistad. A continuación se detallan los pasos para inicializar la aplicación en tu máquina local.

## Requisitos Previos

1. **Docker**: Asegúrate de tener [Docker](https://docs.docker.com/get-docker/) instalado en tu máquina.
2. **Python**: Necesitas tener Python 3.6 o superior instalado.
3. **pip**: Asegúrate de tener `pip` para instalar las dependencias de Python.
4. [Cargar la Lista de Adyacencia](##cargar-la-lista-de-adyacencia)

## Clonación del Repositorio

Clona este repositorio en tu máquina local:

```bash
git clone https://github.com/codelock54/SocialNetworks.git
cd SocialNetworks
docker pull neo4j
docker-compose up -d 
```

## Cargar la Lista de Adyacencia


```python
import SocialNetworks

friends = SocialNetworks.SocialNetwork()
adjacency_list = friends.read_adjacency_list_from_file('lista_adyacencia.txt')
friends.load_adjacency_list(adjacency_list)

friends.plot_friends()
```
## Crear la Lista de Adyacencia

```python
import SocialNetworks

friends = SocialNetworks.SocialNetwork()
friends.crearte_adList()
friends.print_List()
```
