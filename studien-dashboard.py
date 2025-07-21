from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, date
from typing import List, Dict, Optional, Union
import json


class IUBewertungsmaßstab:
    """Einheitlicher Bewertungsmaßstab der IU Internationale Hochschule"""

    NOTEN_SKALA = {
        1.0: "Sehr gut",
        1.3: "Sehr gut",
        1.7: "Gut", 
        2.0: "Gut",
        2.3: "Gut",
        2.7: "Befriedigend",
        3.0: "Befriedigend", 
        3.3: "Befriedigend",
        3.7: "Ausreichend",
        4.0: "Ausreichend",
        5.0: "Nicht ausreichend"
    }

    BESTANDEN_GRENZE = 4.0

    @classmethod
    def ist_bestanden(cls, note: float) -> bool:
        return note <= cls.BESTANDEN_GRENZE

    @classmethod
    def note_zu_text(cls, note: float) -> str:
        return cls.NOTEN_SKALA.get(note, "Ungültige Note")

    @classmethod
    def gueltige_noten(cls) -> List[float]:
        return list(cls.NOTEN_SKALA.keys())


class PruefungsleistungsTyp(Enum):
    """Nur die benötigten Prüfungsleistungstypen für IU Medizinische Informatik"""
    KLAUSUR = "Klausur"
    ADVANCED_WORKBOOK = "Advanced Workbook"
    PORTFOLIO = "Portfolio"


class StudiengangTyp(Enum):
    BACHELOR = "Bachelor"
    MASTER = "Master"
    MBA = "MBA"


class ModulStatus(Enum):
    NICHT_BEGONNEN = "Nicht begonnen"
    IN_BEARBEITUNG = "In Bearbeitung"
    BESTANDEN = "Bestanden"
    NICHT_BESTANDEN = "Nicht bestanden"


class Pruefungsleistung(ABC):
    def __init__(self, typ: PruefungsleistungsTyp, note: Optional[float] = None, 
                 datum: Optional[date] = None, versuch: int = 1):
        self.typ = typ
        self._note = note
        self.datum = datum
        self.versuch = versuch
        self.status = "Offen"

    @property
    def note(self) -> Optional[float]:
        return self._note

    @note.setter
    def note(self, value: Optional[float]):
        if value is not None:
            if value not in IUBewertungsmaßstab.gueltige_noten():
                raise ValueError(f"Ungültige Note: {value}")
            self._note = value
            self.status = "Bestanden" if IUBewertungsmaßstab.ist_bestanden(value) else "Nicht bestanden"
        else:
            self._note = None
            self.status = "Offen"

    def ist_bestanden(self) -> bool:
        return self.note is not None and IUBewertungsmaßstab.ist_bestanden(self.note)

    def wurde_abgelegt(self) -> bool:
        return self.note is not None

    @abstractmethod
    def get_details(self) -> Dict:
        pass

    def to_dict(self) -> Dict:
        return {
            'typ': self.typ.value,
            'note': self.note,
            'datum': self.datum.isoformat() if self.datum else None,
            'versuch': self.versuch,
            'status': self.status,
            'details': self.get_details()
        }


class Klausur(Pruefungsleistung):
    def __init__(self, dauer_minuten: int = 120, **kwargs):
        super().__init__(PruefungsleistungsTyp.KLAUSUR, **kwargs)
        self.dauer_minuten = dauer_minuten

    def get_details(self) -> Dict:
        return {
            'dauer_minuten': self.dauer_minuten,
            'beschreibung': f'Klausur ({self.dauer_minuten} Min.)'
        }


class AdvancedWorkbook(Pruefungsleistung):
    def __init__(self, bearbeitungszeit_wochen: int = 4, **kwargs):
        super().__init__(PruefungsleistungsTyp.ADVANCED_WORKBOOK, **kwargs)
        self.bearbeitungszeit_wochen = bearbeitungszeit_wochen

    def get_details(self) -> Dict:
        return {
            'bearbeitungszeit_wochen': self.bearbeitungszeit_wochen,
            'beschreibung': f'Advanced Workbook ({self.bearbeitungszeit_wochen} Wochen)'
        }


class Portfolio(Pruefungsleistung):
    def __init__(self, anzahl_aufgaben: int = 3, bearbeitungszeit_wochen: int = 8, **kwargs):
        super().__init__(PruefungsleistungsTyp.PORTFOLIO, **kwargs)
        self.anzahl_aufgaben = anzahl_aufgaben
        self.bearbeitungszeit_wochen = bearbeitungszeit_wochen

    def get_details(self) -> Dict:
        return {
            'anzahl_aufgaben': self.anzahl_aufgaben,
            'bearbeitungszeit_wochen': self.bearbeitungszeit_wochen,
            'beschreibung': f'Portfolio ({self.anzahl_aufgaben} Aufgaben)'
        }


class Modul:
    def __init__(self, titel: str, ects: int, pflicht: bool = True):
        self.titel = titel
        self.ects = ects
        self.pflicht = pflicht
        self.pruefungsleistungen: List[Pruefungsleistung] = []

    def add_pruefungsleistung(self, pruefungsleistung: Pruefungsleistung):
        self.pruefungsleistungen.append(pruefungsleistung)

    def ist_bestanden(self) -> bool:
        if not self.pruefungsleistungen:
            return False
        return all(pl.ist_bestanden() for pl in self.pruefungsleistungen)

    def get_status(self) -> ModulStatus:
        if not self.pruefungsleistungen:
            return ModulStatus.NICHT_BEGONNEN
        alle_abgelegt = all(pl.wurde_abgelegt() for pl in self.pruefungsleistungen)
        if alle_abgelegt:
            return ModulStatus.BESTANDEN if self.ist_bestanden() else ModulStatus.NICHT_BESTANDEN
        else:
            return ModulStatus.IN_BEARBEITUNG

    def erreichte_ects(self) -> int:
        return self.ects if self.ist_bestanden() else 0

    def get_durchschnittsnote(self) -> Optional[float]:
        noten = [pl.note for pl in self.pruefungsleistungen if pl.note is not None]
        if not noten:
            return None
        return round(sum(noten) / len(noten), 1)

    def to_dict(self) -> Dict:
        return {
            'titel': self.titel,
            'ects': self.ects,
            'pflicht': self.pflicht,
            'status': self.get_status().value,
            'durchschnittsnote': self.get_durchschnittsnote(),
            'pruefungsleistungen': [pl.to_dict() for pl in self.pruefungsleistungen]
        }


class Semester:
    def __init__(self, nummer: int, startdatum: date, enddatum: date):
        self.nummer = nummer
        self.startdatum = startdatum
        self.enddatum = enddatum
        self.module: List[Modul] = []

    def add_modul(self, modul: Modul):
        self.module.append(modul)

    def erreichte_ects(self) -> int:
        return sum(modul.erreichte_ects() for modul in self.module)

    def gesamt_ects_semester(self) -> int:
        return sum(modul.ects for modul in self.module)

    def durchschnittsnote(self) -> Optional[float]:
        gewichtete_summe = 0
        gesamt_ects = 0
        for modul in self.module:
            if modul.ist_bestanden():
                note = modul.get_durchschnittsnote()
                if note is not None:
                    gewichtete_summe += note * modul.ects
                    gesamt_ects += modul.ects
        return round(gewichtete_summe / gesamt_ects, 1) if gesamt_ects > 0 else None

    def to_dict(self) -> Dict:
        return {
            'nummer': self.nummer,
            'startdatum': self.startdatum.isoformat(),
            'enddatum': self.enddatum.isoformat(),
            'gesamt_ects': self.gesamt_ects_semester(),
            'erreichte_ects': self.erreichte_ects(),
            'durchschnittsnote': self.durchschnittsnote(),
            'module': [modul.to_dict() for modul in self.module]
        }


class Studiengang:
    def __init__(self, name: str, abschluss: str, typ: StudiengangTyp, 
                 start_studium: date, ziel_note: float = 2.0, 
                 ziel_dauer_semester: int = 6):
        self.name = name
        self.abschluss = abschluss
        self.typ = typ
        self.start_studium = start_studium
        self.ziel_note = ziel_note
        self.ziel_dauer_semester = ziel_dauer_semester
        self.semester: List[Semester] = []

    def add_semester(self, semester: Semester):
        self.semester.append(semester)

    def berechne_gesamt_ects(self) -> int:
        return sum(semester.erreichte_ects() for semester in self.semester)

    def berechne_gesamtnote(self) -> Optional[float]:
        gewichtete_summe = 0
        gesamt_ects = 0
        for semester in self.semester:
            for modul in semester.module:
                if modul.ist_bestanden():
                    note = modul.get_durchschnittsnote()
                    if note is not None:
                        gewichtete_summe += note * modul.ects
                        gesamt_ects += modul.ects
        return round(gewichtete_summe / gesamt_ects, 1) if gesamt_ects > 0 else None

    def ist_im_zeitplan(self) -> bool:
        aktuelles_semester = len(self.semester)
        return aktuelles_semester <= self.ziel_dauer_semester

    def ziel_erreicht(self) -> bool:
        gesamtnote = self.berechne_gesamtnote()
        return gesamtnote is not None and gesamtnote <= self.ziel_note

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'abschluss': self.abschluss,
            'typ': self.typ.value,
            'start_studium': self.start_studium.isoformat(),
            'ziel_note': self.ziel_note,
            'ziel_dauer_semester': self.ziel_dauer_semester,
            'gesamt_ects': self.berechne_gesamt_ects(),
            'gesamtnote': self.berechne_gesamtnote(),
            'im_zeitplan': self.ist_im_zeitplan(),
            'ziel_erreicht': self.ziel_erreicht(),
            'semester': [semester.to_dict() for semester in self.semester]
        }


class User:
    def __init__(self, user_id: str, name: str, email: str, rolle: str = "Student"):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.rolle = rolle
        self.studiengaenge: List[Studiengang] = []
        self.erstellt_am = datetime.now()

    def add_studiengang(self, studiengang: Studiengang):
        self.studiengaenge.append(studiengang)

    def get_aktueller_studiengang(self) -> Optional[Studiengang]:
        return self.studiengaenge[-1] if self.studiengaenge else None

    def zeige_dashboard(self) -> Dict:
        aktueller_studiengang = self.get_aktueller_studiengang()
        if not aktueller_studiengang:
            return {"error": "Kein Studiengang gefunden"}
        return {
            'user': {
                'name': self.name,
                'email': self.email,
                'rolle': self.rolle
            },
            'studiengang': aktueller_studiengang.to_dict(),
            'fortschritt': {
                'gesamt_ects': aktueller_studiengang.berechne_gesamt_ects(),
                'gesamtnote': aktueller_studiengang.berechne_gesamtnote(),
                'im_zeitplan': aktueller_studiengang.ist_im_zeitplan(),
                'ziel_erreicht': aktueller_studiengang.ziel_erreicht()
            }
        }


class DashboardController:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.current_user: Optional[User] = None

    def create_user(self, user_id: str, name: str, email: str, rolle: str = "Student") -> User:
        user = User(user_id, name, email, rolle)
        self.users[user_id] = user
        return user

    def login_user(self, user_id: str) -> bool:
        if user_id in self.users:
            self.current_user = self.users[user_id]
            return True
        return False

    def create_studiengang(self, name: str, abschluss: str, typ: StudiengangTyp,
                          start_studium: date, ziel_note: float = 2.0,
                          ziel_dauer_semester: int = 6) -> Optional[Studiengang]:
        if not self.current_user:
            return None
        studiengang = Studiengang(name, abschluss, typ, start_studium, ziel_note, ziel_dauer_semester)
        self.current_user.add_studiengang(studiengang)
        return studiengang

    def create_pruefungsleistung(self, typ: PruefungsleistungsTyp, **kwargs) -> Pruefungsleistung:
        """Factory-Methode für Prüfungsleistungen"""
        if typ == PruefungsleistungsTyp.KLAUSUR:
            return Klausur(**kwargs)
        elif typ == PruefungsleistungsTyp.ADVANCED_WORKBOOK:
            return AdvancedWorkbook(**kwargs)
        elif typ == PruefungsleistungsTyp.PORTFOLIO:
            return Portfolio(**kwargs)
        else:
            raise ValueError(f"Unbekannter Prüfungsleistungstyp: {typ}")

    def get_dashboard_data(self) -> Optional[Dict]:
        if not self.current_user:
            return None
        return self.current_user.zeige_dashboard()


class DashboardVisualization:
    """Klasse für die Erstellung der Dashboard-Visualisierung"""
    
    def __init__(self, controller):
        self.controller = controller
    
    def generate_html_dashboard(self) -> str:
        """Generiert das HTML-Dashboard mit den IU-spezifischen Modulen"""
        dashboard_data = self.controller.get_dashboard_data()
        if not dashboard_data:
            return "<p>Keine Dashboard-Daten verfügbar</p>"
        
        studiengang = dashboard_data['studiengang']
        user = dashboard_data['user']
        
        # Berechne Gesamtfortschritt (180 ECTS für Bachelor Medizinische Informatik)
        gesamt_ects_ziel = 180
        erreichte_ects = studiengang['gesamt_ects']
        fortschritt_prozent = round((erreichte_ects / gesamt_ects_ziel) * 100)
        
        # Aktuelles Semester ermitteln
        aktuelles_semester = len(studiengang['semester'])
        
        # Zielnote vs. aktuelle Note
        ziel_note = studiengang['ziel_note']
        aktuelle_note = studiengang['gesamtnote'] or 0.0
        note_differenz = round(ziel_note - aktuelle_note, 1) if aktuelle_note > 0 else 0
        
        html = f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>IU Studiendashboard - {user['name']}</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #f5f5f5;
                    color: #333;
                    line-height: 1.6;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                
                .dashboard-header {{
                    display: grid;
                    grid-template-columns: 1fr 1fr 1fr;
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                
                .card {{
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    border: 1px solid #e0e0e0;
                }}
                
                .card h3 {{
                    font-size: 14px;
                    font-weight: 600;
                    color: #666;
                    margin-bottom: 15px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                
                .progress-card {{
                    position: relative;
                }}
                
                .progress-circle {{
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    background: conic-gradient(#4CAF50 0deg {fortschritt_prozent * 3.6}deg, #e0e0e0 {fortschritt_prozent * 3.6}deg 360deg);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-bottom: 10px;
                }}
                
                .progress-inner {{
                    width: 60px;
                    height: 60px;
                    background: white;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    color: #4CAF50;
                }}
                
                .ects-display {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 5px;
                }}
                
                .note-display {{
                    font-size: 48px;
                    font-weight: bold;
                    color: #4CAF50;
                    margin-bottom: 10px;
                }}
                
                .note-improvement {{
                    color: #4CAF50;
                    font-size: 14px;
                }}
                
                .status-good {{
                    color: #4CAF50;
                    font-weight: 500;
                }}
                
                .navigation {{
                    display: flex;
                    background: white;
                    border-radius: 12px;
                    margin-bottom: 20px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                
                .nav-item {{
                    flex: 1;
                    padding: 15px 20px;
                    text-align: center;
                    cursor: pointer;
                    border-right: 1px solid #e0e0e0;
                    transition: background-color 0.3s;
                }}
                
                .nav-item:last-child {{
                    border-right: none;
                }}
                
                .nav-item.active {{
                    background-color: #4CAF50;
                    color: white;
                    font-weight: 600;
                }}
                
                .nav-item:hover:not(.active) {{
                    background-color: #f0f0f0;
                }}
                
                .module-section {{
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                
                .section-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                }}
                
                .section-title {{
                    font-size: 20px;
                    font-weight: 600;
                    color: #333;
                }}
                
                .add-button {{
                    background: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-weight: 500;
                }}
                
                .semester-select {{
                    margin-bottom: 20px;
                }}
                
                .semester-select select {{
                    padding: 10px 15px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 14px;
                    min-width: 200px;
                }}
                
                .module-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                
                .module-table th {{
                    background: #4CAF50;
                    color: white;
                    padding: 15px;
                    text-align: left;
                    font-weight: 600;
                }}
                
                .module-table td {{
                    padding: 15px;
                    border-bottom: 1px solid #e0e0e0;
                    vertical-align: top;
                }}
                
                .module-table tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                
                .status-badge {{
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    font-weight: 500;
                }}
                
                .status-badge.passed {{
                    color: #4CAF50;
                }}
                
                .status-badge.in-progress {{
                    color: #FF9800;
                }}
                
                .status-badge.not-started {{
                    color: #999;
                }}
                
                .checkmark {{
                    color: #4CAF50;
                    font-weight: bold;
                }}
                
                .summary-row {{
                    background: #f0f8f0 !important;
                    font-weight: 600;
                }}
                
                .footer {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-top: 20px;
                    padding: 15px 20px;
                    background: #f9f9f9;
                    border-radius: 8px;
                    font-size: 14px;
                    color: #666;
                }}
                
                .module-title {{
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 3px;
                }}
                
                .module-subtitle {{
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Dashboard Header Cards -->
                <div class="dashboard-header">
                    <div class="card progress-card">
                        <h3>GESAMTFORTSCHRITT</h3>
                        <div class="progress-circle">
                            <div class="progress-inner">{fortschritt_prozent}%</div>
                        </div>
                        <div class="ects-display">{erreichte_ects}/{gesamt_ects_ziel} ECTS</div>
                    </div>
                    
                    <div class="card">
                        <h3>NOTENDURCHSCHNITT</h3>
                        <div class="note-display">{aktuelle_note if aktuelle_note > 0 else '—'}</div>
                        {f'<div class="note-improvement">▲ {abs(note_differenz)} besser als Ziel</div>' if note_differenz < 0 else f'<div class="note-improvement">Ziel: {ziel_note}</div>'}
                    </div>
                    
                    <div class="card">
                        <h3>ZEITPLANUNG</h3>
                        <div style="margin-bottom: 10px; font-size: 18px; font-weight: 600;">
                            Aktuell: {aktuelles_semester}. Semester
                        </div>
                        <div class="status-good">✓ Im Zeitplan</div>
                    </div>
                </div>
                
                <!-- Navigation -->
                <div class="navigation">
                    <div class="nav-item active">MODULÜBERSICHT</div>
                    <div class="nav-item">NOTENVERTEILUNG</div>
                    <div class="nav-item">ZEITPLANUNG</div>
                    <div class="nav-item">PRÜFUNGSTERMINE</div>
                </div>
                
                <!-- Module Section -->
                <div class="module-section">
                    <div class="section-header">
                        <h2 class="section-title">Modulübersicht - Medizinische Informatik</h2>
                        <button class="add-button">+ Modul</button>
                    </div>
                    
                    <div class="semester-select">
                        <label>Semesterauswahl: </label>
                        <select>
                            <option>1. Semester</option>
                        </select>
                    </div>
                    
                    <table class="module-table">
                        <thead>
                            <tr>
                                <th>Modul</th>
                                <th>ECTS</th>
                                <th>Prüfungsleistung</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # Module aus dem ersten Semester hinzufügen
        if studiengang['semester']:
            semester_data = studiengang['semester'][0]
            gesamt_ects_semester = 0
            bestandene_module = 0
            durchschnitt_noten = []
            
            for modul in semester_data['module']:
                # Status bestimmen
                if modul['status'] == "Bestanden":
                    status_class = "passed"
                    status_icon = "✓"
                    bestandene_module += 1
                elif modul['status'] == "In Bearbeitung":
                    status_class = "in-progress"
                    status_icon = "○"
                else:
                    status_class = "not-started"
                    status_icon = "○"
                
                note_display = f"{modul['durchschnittsnote']}" if modul['durchschnittsnote'] else "—"
                
                # Prüfungsleistung Details
                pruefungsleistung_text = ""
                if modul['pruefungsleistungen']:
                    pl = modul['pruefungsleistungen'][0]
                    pruefungsleistung_text = pl['details']['beschreibung']
                
                gesamt_ects_semester += modul['ects']
                if modul['durchschnittsnote']:
                    durchschnitt_noten.append(modul['durchschnittsnote'])
                
                html += f"""
                            <tr>
                                <td>
                                    <div class="module-title">{modul['titel']}</div>
                                    <div class="module-subtitle">Pflichtmodul</div>
                                </td>
                                <td>{modul['ects']}</td>
                                <td>{pruefungsleistung_text}</td>
                                <td><span class="status-badge {status_class}"><span class="checkmark">{status_icon}</span> {note_display}</span></td>
                            </tr>
                """
            
            # Zusammenfassung
            semester_durchschnitt = round(sum(durchschnitt_noten) / len(durchschnitt_noten), 1) if durchschnitt_noten else 0
            html += f"""
                            <tr class="summary-row">
                                <td><strong>Gesamt ECTS im Semester: {gesamt_ects_semester}</strong></td>
                                <td><strong>{erreichte_ects}</strong></td>
                                <td><strong>Durchschnitt: {semester_durchschnitt}</strong></td>
                                <td><span class="status-badge passed"><span class="checkmark">✓</span> {bestandene_module}/{len(semester_data['module'])} bestanden</span></td>
                            </tr>
            """
        
        html += """
                        </tbody>
                    </table>
                </div>
                
                <!-- Footer -->
                <div class="footer">
                    <div>Datenstand: 06.05.2025 | IU Internationale Hochschule</div>
                    <div>Nächste Prüfung: Portfolio OOP (in Bearbeitung)</div>
                </div>
            </div>
            
            <script>
                // Navigation functionality
                document.querySelectorAll('.nav-item').forEach(item => {
                    item.addEventListener('click', function() {
                        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
                        this.classList.add('active');
                    });
                });
                
                // Add Module functionality
                document.querySelector('.add-button').addEventListener('click', function() {
                    alert('Modul hinzufügen - Funktionalität würde hier implementiert werden');
                });
            </script>
        </body>
        </html>
        """
        
        return html


# Beispieldaten mit den spezifischen IU-Modulen erstellen
def create_iu_medizinische_informatik_data():
    """Erstellt Beispieldaten mit den spezifischen IU-Modulen für Medizinische Informatik"""
    controller = DashboardController()
    
    # Benutzer erstellen
    user = controller.create_user("IU14125513", "Christine Münzberg", "christine_muenzberg@web.de")
    controller.login_user("IU14125513")
    
    # Studiengang erstellen
    studiengang = controller.create_studiengang(
        "Medizinische Informatik", 
        "Bachelor of Science", 
        StudiengangTyp.BACHELOR,
        date(2025, 1, 1),
        ziel_note=2.0,
        ziel_dauer_semester=8
    )
    
    # Erstes Semester erstellen
    semester1 = Semester(1, date(2025, 1, 1), date(2025, 6, 30))
    studiengang.add_semester(semester1)
    
    # Module mit IU-spezifischen Prüfungsleistungen erstellen

    # Einführung in das wissenschaftliche Arbeiten für IT und Technik - Advanced Workbook
    einfuehrung_wiss = Modul("Einführung in das wissenschaftliche Arbeiten für IT und Technik", 5, True)
    workbook_wiss = controller.create_pruefungsleistung(
        PruefungsleistungsTyp.ADVANCED_WORKBOOK,
        bearbeitungszeit_wochen=6,
        note=2.0,
        datum=date(2025, 3, 29)
    )
    einfuehrung_wiss.add_pruefungsleistung(workbook_wiss)
    semester1.add_modul(einfuehrung_wiss)

    # Medizin für Nichtmediziner:innen I - Klausur
    medizin_nichtmed = Modul("Medizin für Nichtmediziner:innen I", 5, True)
    klausur_med = controller.create_pruefungsleistung(
        PruefungsleistungsTyp.KLAUSUR,
        dauer_minuten=90,
        note=3.3,
        datum=date(2024, 12, 10)
    )
    medizin_nichtmed.add_pruefungsleistung(klausur_med)
    semester1.add_modul(medizin_nichtmed)

    # Einführung in die Programmierung mit Python - Klausur
    programmierung_python = Modul("Einführung in die Programmierung mit Python", 5, True)
    klausur_prog = controller.create_pruefungsleistung(
        PruefungsleistungsTyp.KLAUSUR,
        dauer_minuten=90,
        note=2.0,
        datum=date(2025, 3, 1)
    )
    programmierung_python.add_pruefungsleistung(klausur_prog)
    semester1.add_modul(programmierung_python)

    # E-Health - Klausur
    ehealth = Modul("E-Health", 5, True)
    klausur_ehealth = controller.create_pruefungsleistung(
        PruefungsleistungsTyp.KLAUSUR,
        dauer_minuten=90,
        note=2.0,
        datum=date(2025, 2, 1)
    )
    ehealth.add_pruefungsleistung(klausur_ehealth)
    semester1.add_modul(ehealth)

    # Projekt: Objektorientierte und funktionale Programmierung mit Python - Portfolio
    projekt_oop = Modul("Projekt: Objektorientierte und funktionale Programmierung mit Python", 5, True)
    portfolio_oop = controller.create_pruefungsleistung(
        PruefungsleistungsTyp.PORTFOLIO,
        anzahl_aufgaben=4,
        bearbeitungszeit_wochen=6
        # Keine Note gesetzt - noch in Bearbeitung
    )
    projekt_oop.add_pruefungsleistung(portfolio_oop)
    semester1.add_modul(projekt_oop)
    
    return controller


# Dashboard generieren und als HTML-Datei speichern
controller = create_iu_medizinische_informatik_data()
dashboard_viz = DashboardVisualization(controller)
html_content = dashboard_viz.generate_html_dashboard()

# HTML-Datei erstellen
with open('iu_dashboard_final.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("✅ Bereinigtes IU Dashboard wurde erfolgreich erstellt!")
print("📁 Datei: iu_dashboard_final.html")
print("🎓 Studiengang: Medizinische Informatik (Bachelor of Science)")
print("👤 Student: Christine Münzberg (IU14125513)")
print("\n" + "="*70)
print("🗑️  ENTFERNTE PRÜFUNGSLEISTUNGSTYPEN:")
print("❌ FALLSTUDIE")
print("❌ HAUSARBEIT") 
print("❌ PRAKTISCHE_PRUEFUNG")
print("❌ PROJEKT")
print("\n✅ VERBLEIBENDE PRÜFUNGSLEISTUNGSTYPEN:")
print("✓ KLAUSUR")
print("✓ ADVANCED_WORKBOOK")
print("✓ PORTFOLIO")
print("\n📚 MODULE IM 1. SEMESTER:")
print("✅ Einführung in das wissenschaftliche Arbeiten für IT und Technik (5 ECTS) - Advanced Workbook - Note: 2.0")
print("✅ Medizin für Nichtmediziner:innen I (5 ECTS) - Klausur - Note: 3.3")
print("✅ Einführung in die Programmierung mit Python (5 ECTS) - Klausur - Note: 2.0")
print("✅ E-Health (5 ECTS) - Klausur - Note: 2.0")
print("🔄 Projekt: Objektorientierte und funktionale Programmierung mit Python (5 ECTS) - Portfolio - In Bearbeitung")
print("="*70)
print("📊 STATISTIKEN:")
print("• Erreichte ECTS: 20/25 (80%)")
print("• Durchschnittsnote: 2.3")
print("• Fortschritt: 11% (20/180 ECTS)")
print("• Status: Im Zeitplan")
print("="*70)
