import streamlit as st
from streamlit_folium import st_folium
from trip_components import LLMHandler, GeocodingHandler, MapHandler

def main():
    st.title("🗺️ AI Trip Planner")
    st.write("Plan your perfect trip with AI-powered recommendations!")
    
    # Initialize session state
    if 'spots_with_coords' not in st.session_state:
        st.session_state.spots_with_coords = None
    if 'current_location' not in st.session_state:
        st.session_state.current_location = None
    
    # Initialize handlers
    llm_handler = LLMHandler()
    geocoding_handler = GeocodingHandler()
    map_handler = MapHandler()
    
    # User Input Form
    with st.form("trip_form"):
        st.subheader("Trip Details")
        
        location = st.text_input("Destination", placeholder="e.g., Paris, France")
        duration = st.selectbox("Trip Duration", ["1 day", "2-3 days", "4-7 days", "1+ weeks"])
        category = st.selectbox("What interests you?", [
            "Tourist attractions", 
            "Hidden gems", 
            "Nature & outdoors", 
            "Local food", 
            "Culture & history"
        ])
        num_spots = st.slider("Number of spots", 2, 5, 3)
        
        submitted = st.form_submit_button("Get Recommendations")
    
    # Process and Display Results
    if submitted and location:
        with st.spinner("Finding amazing spots for you..."):
            # Get LLM recommendations
            spots_data = llm_handler.get_recommendations(location, duration, category, num_spots)
            
            if spots_data:
                # Get coordinates for each spot
                spots_with_coords = geocoding_handler.get_coordinates(spots_data, location)
                
                if spots_with_coords:
                    # Store in session state
                    st.session_state.spots_with_coords = spots_with_coords
                    st.session_state.current_location = location
                else:
                    st.error("Could not find coordinates for the recommended spots. Try a different location.")
                    st.session_state.spots_with_coords = None
            else:
                st.error("Could not generate recommendations. Please try again.")
                st.session_state.spots_with_coords = None
    
    # Display results if they exist in session state
    if st.session_state.spots_with_coords:
        st.subheader(f"Recommended spots in {st.session_state.current_location}")
        
        # Create and display map
        map_obj = map_handler.create_map(st.session_state.spots_with_coords)
        if map_obj is not None:
            map_data = st_folium(map_obj, width=700, height=500, key="trip_map")
        else:
            st.error("Could not create map for the selected spots.")
        
        # Display spot details
        st.subheader("Spot Details")
        for spot in st.session_state.spots_with_coords:
            with st.expander(f"📍 {spot['name']}"):
                st.write(spot['remarks'])
        
        # Add clear button
        if st.button("Clear Results"):
            st.session_state.spots_with_coords = None
            st.session_state.current_location = None
            st.rerun()

if __name__ == "__main__":
    main()