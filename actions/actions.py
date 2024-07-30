# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []
import os
import time
from typing import Any, Text, Dict, List
import pandas as pd
import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

# Clase para interactuar con la base de datos de restaurantes
class RestaurantAPI(object):

    def __init__(self):
        # Cargar la base de datos de restaurantes desde un archivo CSV
        self.db = pd.read_csv("C:/Users/Diego/Desktop/Workshop_UPC/restaurants.csv")

    # Método para obtener los primeros registros de la base de datos
    def fetch_restaurants(self):
        return self.db.head()

    # Método para formatear los datos de los restaurantes como una cadena CSV
    def format_restaurants(self, df, header=True) -> Text:
        return df.to_csv(index=False, header=header)

# Clase para interactuar con la API de ChatGPT
class ChatGPT(object):

    def __init__(self):
        self.url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-3.5-turbo"
        # Cabeceras de la solicitud HTTP, incluyendo la clave de autorización
        self.headers={
            "Content-Type": "application/json",
            "Authorization": "XXX"
        }
        # Prompt inicial para guiar las respuestas de ChatGPT
        self.prompt = "Answer the following question, based on the data shown. " \
            "Answer in a complete sentence and don't say anything else."

    # Método para hacer una pregunta a ChatGPT basada en los datos de restaurantes
    def ask(self, restaurants, question, retries=3, backoff_factor=1.0):
        content = self.prompt + "\n\n" + restaurants + "\n\n" + question
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}]
        }
        for attempt in range(retries):
            try:
                result = requests.post(
                    url=self.url,
                    headers=self.headers,
                    json=body,
                )
                result.raise_for_status()  # Verificar si hubo algún error en la respuesta
                response = result.json()
                if "choices" in response and len(response["choices"]) > 0:
                    return response["choices"][0]["message"]["content"]
                else:
                    print(f"Respuesta inesperada de la API de ChatGPT: {response}")
                    return "Lo siento, hubo un problema al procesar tu solicitud. Por favor, inténtalo de nuevo más tarde."
            except requests.exceptions.RequestException as e:
                if result.status_code == 429:
                    print(f"Error 429: Too Many Requests. Reintentando en {backoff_factor} segundos...")
                    time.sleep(backoff_factor)
                    backoff_factor *= 2  # Incrementar el tiempo de espera exponencialmente
                else:
                    print(f"Error al conectar con la API de ChatGPT: {e}")
                    return "Lo siento, hubo un problema al procesar tu solicitud. Por favor, inténtalo de nuevo más tarde."
        return "Lo siento, hemos excedido el número de intentos para procesar tu solicitud. Por favor, inténtalo de nuevo más tarde."

# Crear instancias de las clases API de restaurantes y ChatGPT
restaurant_api = RestaurantAPI()
chatGPT = ChatGPT()

# Acción para mostrar restaurantes
class ActionShowRestaurants(Action):

    def name(self) -> Text:
        return "action_show_restaurants"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Obtener los primeros restaurantes de la base de datos
        restaurants = restaurant_api.fetch_restaurants()
        # Formatear los datos completos de los restaurantes como cadena CSV
        results = restaurant_api.format_restaurants(restaurants)
        # Formatear una versión legible de los datos de los restaurantes, sin encabezado
        readable = restaurant_api.format_restaurants(restaurants[['Restaurants', 'Rating']], header=False)
        # Enviar un mensaje al usuario con los restaurantes formateados
        dispatcher.utter_message(text=f"Here are some restaurants:\n\n{readable}")

        # Devolver un evento para guardar los resultados en una ranura
        return [SlotSet("results", results)]

# Acción para proporcionar detalles de los restaurantes en función de una pregunta
class ActionRestaurantsDetail(Action):
    def name(self) -> Text:
        return "action_restaurants_detail"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Obtener los resultados anteriores almacenados en la ranura
        previous_results = tracker.get_slot("results")
        # Obtener la última pregunta del usuario
        question = tracker.latest_message["text"]
        
        if not previous_results:
            dispatcher.utter_message(text="No hay datos de restaurantes disponibles en este momento.")
            return []

        try:
            # Preguntar a ChatGPT usando los resultados anteriores y la pregunta del usuario
            answer = chatGPT.ask(previous_results, question)
            # Enviar la respuesta de ChatGPT al usuario
            dispatcher.utter_message(text=answer)
        except Exception as e:
            print(f"Error en la acción 'action_restaurants_detail': {e}")
            dispatcher.utter_message(text="Lo siento, hubo un problema al procesar tu solicitud. Por favor, inténtalo de nuevo más tarde.")
        
        return []
        
##############################################################################################################################################################################

import openai
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import uuid

openai.api_key = "XXX"

from rasa_sdk import Tracker, ValidationAction
from rasa_sdk.types import DomainDict

class ActionFallBack(Action):
    def name(self) -> Text:
        return "action_out_of_scope"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        print(tracker)
        query = tracker.latest_message["text"]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ]
        )
        dispatcher.utter_message(text=response.choices[0]['message']['content'])
        return[]