import pandas as pd
import re
import requests

from bs4 import BeautifulSoup

# All playing positions

current_positions = [
    "Goalkeeper",
    "Centre-Back",
    "Left-Back",
    "Right-Back",
    "Defensive Midfield",
    "Central Midfield",
    "Attacking Midfield",
    "Right Midfield",
    "Left Winger",
    "Right Winger",
    "Centre-Forward"
]


# Extract Playing Positions from Player names

def extract_position(text):
    """ A function that extracts a player's position from the Transfermarkt Player column.

        Parameters:
            text (str):
                A string containing both the player's name and position.

        Returns:
            str or None: The identified position if found. Returns None if no known position is detected.

    """

    for pos in current_positions:
        if text.endswith(pos):
            return pos
    return None


# Extract Player Names

def extract_player_name(text, position):
    """A function to extract the player's name from the Transfermarkt Player column.

    Parameters:
        text (str): Original Player column value containing both player name and position.

        position (str): Position extracted from the Player column.

    Returns:
        str: A clean player name with the position removed.
    """

    if position is None:
        return text.strip()

    return text.replace(position, "").strip()


# Convert Market Value from characters to numbers

def convert_market_value(value):
    """To convert Transfermarkt market values from strings into numeric values.

    Parameters:
        value (str): Player Market value string from Transfermarkt

    Returns:
        float: Market value in euros.
    """

    value = value.replace("€", "")

    if "m" in value:
        return float(value.replace("m", "")) * 1_000_000

    elif "k" in value:
        return float(value.replace("k", "")) * 1_000

    return None


# Clean transfermarket data for every squad/clubs

def clean_transfermarkt_squad(df, club, season):
    """Clean and transform a Transfermarkt squad table.

        This function processes a raw Transfermarkt squad DataFrame by:
            - Removing rows with missing market values.
            - Extracting player positions from the Player column.
            - Extracting player names from the Player column.
            - Converting market values from text format into numeric values.
            - Adding club and season identifiers.
            - Returning a simplified dataset suitable for analysis.

        Parameters:

            df (pandas.DataFrame): Raw Transfermarkt squad table.

            club (str): Name of the football club.

            season (str): Season identifier (e.g. '2122', '2223').

        Returns:

            pandas.DataFrame: Cleaned squad dataset containing player name, position, age, market value, club, and season.
    """

    df = df[df["Market value"].notna()].copy()
    df = df[df["Age"].notna()].copy()

    # extract positions

    df["position"] = df["Player"].apply(extract_position)

    # extract player name

    df["player_name"] = df.apply(
        lambda row: extract_player_name(
            row["Player"],
            row["position"]
        ),
        axis=1
    )

    # convert market value

    df["market_value_eur"] = (
        df["Market value"]
        .apply(convert_market_value)
    )

    df["club"] = club
    df["season"] = season

    return df[
        [
            "player_name",
            "position",
            "Age",
            "market_value_eur",
            "club",
            "season"
        ]
    ]

# get clubs for each league

def get_league_clubs(league_url):
    """Extract club names and club IDs from a transfermarkt league page.

    Parameters:
        league_url : str
            Transfermarkt league URL.

    Returns:
        pd.DataFrame
            DataFrame containing:

            - club_name
            - club_id
            - squad_url
    """

    html = requests.get(
        league_url,
        headers={"User-Agent": "Mozilla/5.0"}
    ).text

    soup = BeautifulSoup(html, "html.parser")

    club_links = []

    for link in soup.find_all("a"):

        href = link.get("href")

        if href and "/kader/verein/" in href:
            club_links.append(href)

    unique_clubs = sorted(set(club_links))

    club_records = []

    for club in unique_clubs:

        club_records.append(
            {
                "club_name": (
                    club.split("/")[1]
                    .replace("-", " ")
                    .replace(" amp ", " and ")
                    .title()
                ),
                "club_id": int(
                    re.search(
                        r"verein/(\d+)",
                        club
                    ).group(1)
                ),
                "squad_url": (
                    "https://www.transfermarkt.com"
                    + club
                )
            }
        )

    return pd.DataFrame(club_records)



# collect all squads for multiple seasons

def collect_league_squads(clubs_df, season):
    """
    Collect and clean squad data for all clubs
    in a league.

    Parameters
    ----------
    clubs_df : pd.DataFrame
        Output from get_league_clubs().
    season : str
        Season identifier.

    Returns
    -------
    pd.DataFrame
        Combined squad data for all clubs.
    """

    all_squads = []

    for _, row in clubs_df.iterrows():

        try:
            tables = pd.read_html(row["squad_url"])

            squad_df = clean_transfermarkt_squad(
                tables[1],
                row["club_name"],
                season
            )

            all_squads.append(squad_df)

            print(f"✓ {row['club_name']}")

        #except Exception as e:

            #print(
             #   f"✗ {row['club_name']} : {e}"
            #)
        except Exception as e:
            print(f"✗ {club_name}: {e}")

    return pd.concat(
        all_squads,
        ignore_index=True
    )