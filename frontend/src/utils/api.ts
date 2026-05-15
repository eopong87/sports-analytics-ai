import axios from 'axios';

const API_BASE = 'https://0imys2yzd3.execute-api.us-east-1.amazonaws.com';

export const api = axios.create({ baseURL: API_BASE, timeout: 10000 });

export const fetchNBAScores = () => api.get('/nba/scores');
export const fetchNFLScores = () => api.get('/nfl/scores');
export const fetchMLBScores = () => api.get('/mlb/scores');
export const fetchOdds = () => api.get('/odds/props');
export const fetchAIInsights = () => api.get('/ai/insights');
