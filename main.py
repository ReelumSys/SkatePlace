import folium

def create_advanced_osm_map(center=[52.369, 9.931], zoom=12, output_file="map.html"):
    """
    Erstellt eine Karte mit Markern für Koordinaten und Linien für Straßenabschnitte.
    """
    print(f"Erstelle erweiterte Karte zentriert auf {center}...")
    
    # 1. Karte initialisieren
    my_map = folium.Map(location=center, zoom_start=zoom, control_scale=True)
    
    # --- TEIL 1: Einzelne Koordinaten (Points) ---
    # Liste von Punkten: [Breite, Länge, Name]
    points_of_interest = [
        [52.3758, 9.9331, "Hannover Hauptbahnhof"],
        [52.3692, 9.9310, "Neues Rathaus"],
        [52.3610, 9.9350, "Maschsee"],
    ]
    
    for point in points_of_interest:
        folium.Marker(
            location=[point[0], point[1]],
            popup=point[2],
            tooltip=point[2],
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(my_map)
    
    # --- TEIL 2: Straßenabschnitte / Pfade (LineStrings) ---
    # Liste von Koordinaten, die eine Linie bilden
    # Wir zeichnen hier mal einen kleinen Weg zwischen den Punkten
    route_points = [
        [52.3758, 9.9331], # Start: Hbf
        [52.3720, 9.9320], # Wegpunkt 1
        [52.3692, 9.9310], # Ende: Rathaus
    ]
    
    folium.PolyLine(
        locations=route_points, 
        color="red", 
        weight=5, 
        opacity=0.8,
        tooltip="Straßenabschnitt: Hbf -> Rathaus"
    ).add_to(my_map)
    
    # Speichere die Karte
    my_map.save(output_file)
    print(f"Erfolg! Erweiterte Karte wurde unter {output_file} gespeichert.")

if __name__ == "__main__":
    create_advanced_osm_map()
