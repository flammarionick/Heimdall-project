// src/components/EscapeMap.jsx
import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom red marker for escaped inmates
const escapedIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// Nigerian prison locations (sample data for when inmates don't have escape coords)
const PRISON_LOCATIONS = [
  { name: 'Kirikiri Maximum Security Prison', lat: 6.4541, lng: 3.3841 },
  { name: 'Kuje Prison', lat: 8.8833, lng: 7.2167 },
  { name: 'Port Harcourt Prison', lat: 4.7731, lng: 7.0085 },
  { name: 'Enugu Prison', lat: 6.4584, lng: 7.5464 },
  { name: 'Kaduna Prison', lat: 10.5105, lng: 7.4165 },
  { name: 'Ibadan Prison', lat: 7.3775, lng: 3.9470 },
];

// Component to handle map bounds fitting
function FitBounds({ escapedInmates }) {
  const map = useMap();

  useEffect(() => {
    if (escapedInmates.length > 0) {
      const bounds = L.latLngBounds(
        escapedInmates
          .filter(i => i.escapeLatitude && i.escapeLongitude)
          .map(i => [i.escapeLatitude, i.escapeLongitude])
      );
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50] });
      }
    }
  }, [escapedInmates, map]);

  return null;
}

export default function EscapeMap() {
  const [escapedInmates, setEscapedInmates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchEscaped = async () => {
      try {
        const res = await fetch('/admin/api/inmates/escaped', {
          credentials: 'include'
        });

        if (res.ok) {
          const data = await res.json();
          // Add sample coordinates for inmates without escape location
          const inmatesWithCoords = (data.inmates || []).map((inmate, index) => {
            if (!inmate.escapeLatitude || !inmate.escapeLongitude) {
              // Assign a random prison location for demo purposes
              const prison = PRISON_LOCATIONS[index % PRISON_LOCATIONS.length];
              return {
                ...inmate,
                escapeLatitude: prison.lat + (Math.random() - 0.5) * 0.1,
                escapeLongitude: prison.lng + (Math.random() - 0.5) * 0.1,
                estimatedLocation: prison.name
              };
            }
            return inmate;
          });
          setEscapedInmates(inmatesWithCoords);
        } else {
          setError('Failed to load escaped inmates');
        }
      } catch (err) {
        console.error('Error fetching escaped inmates:', err);
        setError('Failed to connect to server');
      } finally {
        setLoading(false);
      }
    };

    fetchEscaped();
  }, []);

  if (loading) {
    return (
      <div className="h-[400px] bg-gray-100 rounded-xl flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-gray-600 text-sm">Loading escape map...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-[400px] bg-red-50 rounded-xl flex items-center justify-center">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  // Center on Nigeria
  const nigeriaCenter = [9.0820, 8.6753];

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800">Escape Locations Map</h3>
        <p className="text-sm text-gray-500">
          Showing {escapedInmates.length} escaped inmate{escapedInmates.length !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="h-[400px]">
        <MapContainer
          center={nigeriaCenter}
          zoom={6}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {escapedInmates.map((inmate) => (
            <Marker
              key={inmate.db_id || inmate.id}
              position={[inmate.escapeLatitude, inmate.escapeLongitude]}
              icon={escapedIcon}
            >
              <Popup>
                <div className="min-w-[200px]">
                  <div className="flex items-center gap-3 mb-2">
                    {inmate.mugshot ? (
                      <img
                        src={inmate.mugshot}
                        alt={inmate.name}
                        className="w-12 h-12 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center">
                        <span className="text-gray-500 text-lg">?</span>
                      </div>
                    )}
                    <div>
                      <h4 className="font-bold text-gray-800">{inmate.name}</h4>
                      <p className="text-xs text-gray-500">{inmate.id}</p>
                    </div>
                  </div>
                  <div className="space-y-1 text-sm">
                    <p><span className="text-gray-500">Crime:</span> {inmate.crime || 'N/A'}</p>
                    <p><span className="text-gray-500">Risk:</span> <span className={`font-medium ${inmate.riskLevel === 'High' ? 'text-red-600' : inmate.riskLevel === 'Medium' ? 'text-orange-600' : 'text-green-600'}`}>{inmate.riskLevel}</span></p>
                    <p><span className="text-gray-500">Escaped:</span> {inmate.escapeDate ? new Date(inmate.escapeDate).toLocaleDateString() : 'Unknown'}</p>
                    {inmate.estimatedLocation && (
                      <p className="text-xs text-gray-400 italic">Near: {inmate.estimatedLocation}</p>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

          <FitBounds escapedInmates={escapedInmates} />
        </MapContainer>
      </div>

      {escapedInmates.length === 0 && (
        <div className="p-8 text-center text-gray-500">
          No escaped inmates to display on map.
        </div>
      )}
    </div>
  );
}
