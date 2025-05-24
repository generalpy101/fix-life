import pandas as pd

dataset_name = './datasets/games_all_platforms.csv'

GAME_NAME_COLUMNS = ['name', 'title', 'game_title', 'game_name', 'product_name']

# Load the dataset
def load_dataset(file_path):
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
        return None
    except pd.errors.EmptyDataError:
        print("Error: The file is empty.")
        return None
    except pd.errors.ParserError:
        print("Error: There was a parsing error with the file.")
        return None

def process_dataset(df):
    '''
    Return a list of names of games for now
    '''
    if df is None or df.empty:
        return []
    
    # Make column names lowercase
    df.columns = [col.lower() for col in df.columns]

    # Check if the game name type column exists
    game_name_column = None
    for col in GAME_NAME_COLUMNS:
        if col in df.columns:
            game_name_column = col
            break
    if not game_name_column:
        print("Error: No valid game name column found in the dataset.")
        return []
    
    # Extract the 'name' column and convert it to a list
    game_names = df[game_name_column].dropna().tolist()
    # Remove duplicates and strip whitespace
    game_names = list(set(name.strip() for name in game_names if isinstance(name, str)))
    
    return game_names

def get_game_names():
    df = load_dataset(dataset_name)
    game_names = process_dataset(df)
    
    if not game_names:
        print("No game names found in the dataset.")
    else:
        print(f"Found {len(game_names)} game names in the dataset.")
    
    return game_names