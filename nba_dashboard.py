#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jan 12 16:02:24 2025

@author: jf
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from nba_api.stats.endpoints import teamplayerdashboard, leaguedashteamstats, teamgamelog
from nba_api.stats.static import teams
import time
from datetime import datetime

# Function to determine the current season
def get_current_season():
    current_year = datetime.now().year
    current_month = datetime.now().month
    if current_month >= 10:  # NBA season starts in October
        return f"{current_year}-{str(current_year + 1)[-2:]}"
    else:
        return f"{current_year - 1}-{str(current_year)[-2:]}"

# Function to get team ID based on user input
def get_team_id(team_name):
    all_teams = teams.get_teams()
    team = [team for team in all_teams if team['full_name'].lower() == team_name.lower()]
    return team[0]['id'] if team else None

# Function to fetch team game logs and calculate points over recent games
def fetch_team_points_per_game(team_id, season):
    try:
        time.sleep(1)  # Avoid throttling
        game_log = teamgamelog.TeamGameLog(team_id=team_id, season=season).get_data_frames()[0]
        game_log['PTS'] = pd.to_numeric(game_log['PTS'])
        game_log = game_log[['GAME_DATE', 'PTS']].head(10)  # Get last 10 games
        game_log['GAME_DATE'] = pd.to_datetime(game_log['GAME_DATE']).dt.strftime('%Y-%m-%d')
        avg_points = game_log['PTS'].mean()
        return game_log, avg_points
    except Exception as e:
        st.error(f"Error fetching game logs: {e}")
        return pd.DataFrame(), 0

# Function to fetch player stats
def fetch_player_avg_points(team_id, season):
    try:
        time.sleep(1)  # Avoid throttling
        player_dashboard = teamplayerdashboard.TeamPlayerDashboard(team_id=team_id, season=season)
        player_stats = player_dashboard.get_data_frames()[1]  # Player stats DataFrame

        # Calculate PPG for each player
        player_stats['PPG'] = player_stats['PTS'] / player_stats['GP']

        # Exclude injured players (assume players with 0 GP are injured)
        active_players = player_stats[player_stats['GP'] > 0]

        # Include rebounds per game (REB) and assists per game (AST)
        active_players['RPG'] = active_players['REB'] / active_players['GP']
        active_players['APG'] = active_players['AST'] / active_players['GP']

        # Filter top 3 players by PPG
        top_players = active_players.nlargest(3, 'PPG')[['PLAYER_NAME', 'PPG', 'RPG', 'APG']]
        return top_players
    except Exception as e:
        st.error(f"Error fetching player stats: {e}")
        return pd.DataFrame()

# Function to fetch team record
def fetch_team_record(team_id, season):
    try:
        time.sleep(1)  # Avoid throttling
        team_stats = leaguedashteamstats.LeagueDashTeamStats(season=season)
        team_stats_df = team_stats.get_data_frames()[0]
        team_row = team_stats_df[team_stats_df['TEAM_ID'] == team_id]
        if not team_row.empty:
            return team_row.iloc[0]['W_PCT'], team_row
    except Exception as e:
        st.error(f"Error fetching team record: {e}")
    return 0, None

# Streamlit App
st.title("NBA Game Prediction Dashboard")
season = get_current_season()
st.write(f"Data for the {season} season.")

# User input for teams
home_team = st.text_input("Enter the Home Team Name (e.g. Boston Celtics)")
away_team = st.text_input("Enter the Away Team Name (e.g Toronto Raptors")

if home_team and away_team:
    # Fetch team IDs
    team1_id = get_team_id(home_team)
    team2_id = get_team_id(away_team)

    if not team1_id or not team2_id:
        st.error("One or both teams not found. Please check the spelling and try again.")
    else:
        # Fetch and visualize team points per game
        st.header("Team Stats")
        team1_games, team1_avg = fetch_team_points_per_game(team1_id, season)
        team2_games, team2_avg = fetch_team_points_per_game(team2_id, season)

        if not team1_games.empty and not team2_games.empty:
            # Create the line chart for both teams
            fig = go.Figure()

            # Add the first team's line (dark blue)
            fig.add_trace(go.Scatter(
                x=team1_games['GAME_DATE'],
                y=team1_games['PTS'],
                mode='lines',
                name=home_team,  # Explicitly set the name for the legend
                line=dict(color='blue')
            ))

            # Add the second team's line (light blue)
            fig.add_trace(go.Scatter(
                x=team2_games['GAME_DATE'],
                y=team2_games['PTS'],
                mode='lines',
                name=away_team,  # Explicitly set the name for the legend
                line=dict(color='lightblue')
            ))

            # Update the layout for better visualization
            fig.update_layout(
                title=f"{home_team} vs {away_team} Points Per Game (Last 10 Games)",
                xaxis_title="Game Date",
                yaxis_title="Points Per Game",
                legend=dict(
                    title="Teams",
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                )
            )
            st.plotly_chart(fig)

        st.write(f"**{home_team}** Average Points Per Game: {team1_avg:.2f}")
        st.write(f"**{away_team}** Average Points Per Game: {team2_avg:.2f}")

        # Fetch and display player stats
        st.header("Player Stats")
        team1_players = fetch_player_avg_points(team1_id, season)
        team2_players = fetch_player_avg_points(team2_id, season)

        st.subheader(f"{home_team} Top Players")
        st.table(team1_players)

        st.subheader(f"{away_team} Top Players")
        st.table(team2_players)

        # Fetch and visualize win percentage
        st.header("Win Percentage")
        team1_record, _ = fetch_team_record(team1_id, season)
        team2_record, _ = fetch_team_record(team2_id, season)

        if team1_record and team2_record:
            win_data = pd.DataFrame({
                "Team": [home_team, away_team],
                "Win Percentage": [team1_record, team2_record]
            })
            
            # Donut chart visualization
            fig = px.pie(win_data, 
                         names="Team", 
                         values="Win Percentage", 
                         title="Win Percentage Comparison", 
                         hole=0.4)
            fig.update_traces(textinfo='percent+label')
            st.plotly_chart(fig)

        # Predict Outcome
        team1_points = 0.5 + (team1_avg > team2_avg) + (team1_record > team2_record)
        team2_points = (team2_avg > team1_avg) + (team2_record > team1_record)

        st.header("Prediction")
        if team1_points > team2_points:
            st.success(f"Prediction: **{home_team} wins!**")
        elif team2_points > team1_points:
            st.success(f"Prediction: **{away_team} wins!**")
        else:
            st.info("Prediction: It's a tie!")

