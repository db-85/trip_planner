import os
import json
import folium
import requests
from langchain_openai import OpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List

# Pydantic models for structured output
class TravelSpot(BaseModel):
    name: str = Field(description="Name of the travel spot")
    type: str = Field(description="Type/category of the spot")
    remarks: str = Field(description="Brief description and why it's recommended")

class LLMHandler:
    def __init__(self):
        # Initialize OpenAI LLM (requires OPENAI_API_KEY environment variable)
        self.llm = OpenAI(temperature=0.7)
        
        # Set up JSON output parser
        self.parser = JsonOutputParser(pydantic_object=TravelSpot)
        
        # Create prompt template
        self.prompt_template = PromptTemplate(
            template="""
            You are a travel expert. Recommend {num_spots} specific {category} spots in {location} for a {duration} trip.
            
            {format_instructions}
            
            Return a JSON array with the recommendations.
            """,
            input_variables=["location", "duration", "category", "num_spots"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
    
    def get_recommendations(self, location, duration, category, num_spots):
        try:
            # Create the chain using the | operator (new LangChain syntax)
            chain = self.prompt_template | self.llm | self.parser
            
            # Invoke the chain
            response = chain.invoke({
                "location": location,
                "duration": duration,
                "category": category,
                "num_spots": num_spots
            })
            
            # Handle both single object and list responses
            if isinstance(response, list):
                return response
            else:
                return [response]
            
        except Exception as e:
            print(f"LLM Error: {e}")
            # Fallback: try without structured output
            return self._fallback_request(location, duration, category, num_spots)
    
    def _fallback_request(self, location, duration, category, num_spots):
        try:
            simple_prompt = f"""
            Recommend {num_spots} {category} spots in {location} for a {duration} trip.
            Return as JSON array: [{{"name": "Spot Name", "type": "{category}", "remarks": "Description"}}]
            """
            
            response = self.llm.invoke(simple_prompt)
            
            # Try to extract JSON from response
            response_text = response.strip()
            if response_text.startswith('['):
                return json.loads(response_text)
            else:
                # Look for JSON array in the response
                start = response_text.find('[')
                end = response_text.rfind(']') + 1
                if start != -1 and end != 0:
                    return json.loads(response_text[start:end])
            
        except Exception as e:
            print(f"Fallback error: {e}")
            return None

class GeocodingHandler:
    def __init__(self):
        # Using OpenStreetMap Nominatim (free geocoding service)
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            'User-Agent': 'TripPlanner/1.0 (https://example.com/contact)'
        }
    
    def get_coordinates(self, spots_data, location):
        spots_with_coords = []
        
        for spot in spots_data:
            coords = self._geocode_spot(spot['name'], location)
            if coords:
                spot_with_coords = spot.copy()
                spot_with_coords['coordinates'] = coords
                spots_with_coords.append(spot_with_coords)
            else:
                print(f"Could not geocode: {spot['name']}")
        
        return spots_with_coords
    
    def _geocode_spot(self, spot_name, location):
        # Try multiple search strategies
        search_queries = [
            f"{spot_name}, {location}",
            f"{spot_name}",
            f"{location} {spot_name}"
        ]
        
        for query in search_queries:
            try:
                params = {
                    'q': query,
                    'format': 'json',
                    'limit': 1,
                    'addressdetails': 1
                }
                
                response = requests.get(
                    self.base_url, 
                    params=params, 
                    headers=self.headers,
                    timeout=10
                )
                
                # Check if response is successful
                if response.status_code != 200:
                    print(f"API returned status {response.status_code} for {query}")
                    continue
                
                # Check if response has content
                if not response.text.strip():
                    print(f"Empty response for {query}")
                    continue
                
                data = response.json()
                
                if data and len(data) > 0:
                    return {
                        'lat': float(data[0]['lat']),
                        'lon': float(data[0]['lon'])
                    }
                    
            except requests.exceptions.RequestException as e:
                print(f"Request error for {query}: {e}")
                continue
            except (json.JSONDecodeError, ValueError) as e:
                print(f"JSON parsing error for {query}: {e}")
                continue
            except Exception as e:
                print(f"Unexpected error for {query}: {e}")
                continue
        
        return None

class MapHandler:
    def create_map(self, spots_with_coords: List[dict]) -> folium.Map | None:
        if not spots_with_coords or len(spots_with_coords) == 0:
            return None
        
        # Validate that all spots have coordinates
        valid_spots = [spot for spot in spots_with_coords if 
                      'coordinates' in spot and 
                      'lat' in spot['coordinates'] and 
                      'lon' in spot['coordinates']]
        
        if not valid_spots:
            return None
        
        # Calculate center point
        lats = [spot['coordinates']['lat'] for spot in valid_spots]
        lons = [spot['coordinates']['lon'] for spot in valid_spots]
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Add markers for each spot
        colors = ['red', 'blue', 'green', 'purple', 'orange']
        
        for i, spot in enumerate(valid_spots):
            coords = spot['coordinates']
            color = colors[i % len(colors)]
            
            folium.Marker(
                location=[coords['lat'], coords['lon']],
                popup=folium.Popup(
                    f"<b>{spot.get('name', 'Unknown')}</b><br>{spot.get('remarks', 'No description')}",
                    max_width=300
                ),
                tooltip=spot.get('name', 'Unknown location'),
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)
        
        return m