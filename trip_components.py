import os
import json
import folium
import requests
import time
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv

load_dotenv()
email = os.getenv('USER_EMAIL')

class LLMHandler:
    def __init__(self):
        # Initialize OpenAI LLM (requires OPENAI_API_KEY environment variable)
        self.llm = OpenAI(temperature=0.7)
        
        # Create prompt template
        self.prompt_template = PromptTemplate(
            input_variables=["location", "duration", "category", "num_spots"],
            template="""
            You are a travel expert. Recommend {num_spots} specific {category} spots in {location} for a {duration} trip.
            
            Return your response as JSON format with this structure:
            [
                {{
                    "name": "Spot Name",
                    "type": "{category}",
                    "remarks": "Brief description and why it's recommended"
                }}
            ]
            
            Only return the JSON array, no additional text.
            """
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
    
    def get_recommendations(self, location, duration, category, num_spots):
        try:
            response = self.chain.run(
                location=location,
                duration=duration,
                category=category,
                num_spots=num_spots
            )
            
            # Parse JSON response
            spots_data = json.loads(response.strip())
            return spots_data
            
        except Exception as e:
            print(f"LLM Error: {e}")
            return None

class GeocodingHandler:
    def __init__(self):
        # Using OpenStreetMap Nominatim (free geocoding service)
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
        'User-Agent': f'trip_planner/1.0 ({email})'  # Required!
    }
    
    def get_coordinates(self, spots_data, location):
        spots_with_coords = []
        
        for spot in spots_data:
            try:
                # Search for coordinates
                params = {
                    'q': f"{spot['name']}, {location}",
                    'format': 'json',
                    'limit': 1
                }
                
                response = requests.get(self.base_url, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                time.sleep(1)
                
                if data:
                    coords = {
                        'lat': float(data[0]['lat']),
                        'lon': float(data[0]['lon'])
                    }
                    
                    spot_with_coords = spot.copy()
                    spot_with_coords['coordinates'] = coords
                    spots_with_coords.append(spot_with_coords)
                    
            except Exception as e:
                print(f"Geocoding error for {spot['name']}: {e}")
                continue
        
        return spots_with_coords

class MapHandler:
    def create_map(self, spots_with_coords):
        if not spots_with_coords:
            return None
        
        # Calculate center point
        lats = [spot['coordinates']['lat'] for spot in spots_with_coords]
        lons = [spot['coordinates']['lon'] for spot in spots_with_coords]
        
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
        
        for i, spot in enumerate(spots_with_coords):
            coords = spot['coordinates']
            color = colors[i % len(colors)]
            
            folium.Marker(
                location=[coords['lat'], coords['lon']],
                popup=folium.Popup(
                    f"<b>{spot['name']}</b><br>{spot['remarks']}",
                    max_width=300
                ),
                tooltip=spot['name'],
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)
        
        return m