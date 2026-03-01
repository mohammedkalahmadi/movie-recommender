
import os, joblib, warnings
from pathlib import Path
from typing import List, Dict
import numpy as np, pandas as pd
from flask import Flask, request, jsonify, render_template
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import hstack, csr_matrix, save_npz, load_npz

warnings.filterwarnings('ignore', category=FutureWarning)
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DATA_DIR = ROOT_DIR / 'data'
CACHE_DIR = APP_DIR / '.cache'
CACHE_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / 'IMDB_All_Genres_etf_clean1.csv'
COLUMN_ALIASES = {
  'title': ['Movie_Title','Movie title','Title','movie_title','MovieTitle'],
  'main_genre': ['main_genre','Main genre','Main_Genre'],
  'side_genre': ['side_genre','Side genre','Side_Genre'],
  'rating': ['Rating','rating','IMDB_Rating','IMDb Rating'],
  'runtime': ['Runtime','Runtime(Mins)','runtime','Runtime (in minutes)'],
  'year': ['Year','year']
}
_df=None; _X=None; _vectorizer=None; _scaler=None; _kmeans=None; _title_to_idx=None

def resolve_columns(df: pd.DataFrame) -> Dict[str,str]:
  mapping={}; lower={c.lower():c for c in df.columns}
  for key,cands in COLUMN_ALIASES.items():
    for c in cands:
      if c in df.columns: mapping[key]=c; break
      if c.lower() in lower: mapping[key]=lower[c.lower()]; break
    if key not in mapping and key not in ('year',):
      raise KeyError(f"Required column for '{key}' not found. Present: {list(df.columns)}")
  return mapping

def load_data():
  if not DATA_FILE.exists(): return None
  df = pd.read_csv(DATA_FILE)
  col = resolve_columns(df)
  keep=[col.get(k) for k in ('title','main_genre','side_genre','rating','runtime','year') if col.get(k)]
  df=df[keep].copy()
  df[col['title']]=df[col['title']].astype(str).str.strip()
  df[col['main_genre']]=df[col['main_genre']].astype(str).str.strip()
  df[col['side_genre']]=df[col['side_genre']].astype(str).str.strip()
  df[col['rating']]=pd.to_numeric(df[col['rating']], errors='coerce')
  df[col['runtime']]=pd.to_numeric(df[col['runtime']], errors='coerce')
  df=df.dropna(subset=[col['title'],col['main_genre'],col['side_genre'],col['rating'],col['runtime']]).reset_index(drop=True)
  return df

def build_or_load_artifacts(k:int=180):
  global _df,_X,_vectorizer,_scaler,_kmeans,_title_to_idx
  if _df is None:
    _df=load_data()
    if _df is None: return
  vec_p=CACHE_DIR/'vectorizer.joblib'; scl_p=CACHE_DIR/'scaler.joblib'; x_p=CACHE_DIR/'X_sparse.npz'; km_p=CACHE_DIR/f'kmeans_k{k}.joblib'; df_p=CACHE_DIR/'df.pkl'
  if all(p.exists() for p in [vec_p,scl_p,x_p,km_p,df_p]):
    _vectorizer=joblib.load(vec_p); _scaler=joblib.load(scl_p); _X=load_npz(x_p); _kmeans=joblib.load(km_p); _df=joblib.load(df_p)
  else:
    col=resolve_columns(_df)
    text=(_df[col['main_genre']].fillna('')+' '+_df[col['side_genre']].fillna('')).astype(str)
    _vectorizer=CountVectorizer(token_pattern=r'(?u)\b\w+\b'); X_text=_vectorizer.fit_transform(text)
    _scaler=MinMaxScaler(); X_num=_scaler.fit_transform(_df[[col['rating'],col['runtime']]]); X_num=csr_matrix(X_num)
    _X=hstack([X_text,X_num]).tocsr()
    _kmeans=KMeans(n_clusters=k, n_init=10, random_state=42).fit(_X)
    _df['cluster']=_kmeans.labels_
    joblib.dump(_vectorizer,vec_p); joblib.dump(_scaler,scl_p); save_npz(x_p,_X); joblib.dump(_kmeans,km_p); joblib.dump(_df,df_p)
  col=resolve_columns(_df)
  _title_to_idx={t:i for i,t in enumerate(_df[col['title']].tolist())}

def ready():
  return _df is not None and _X is not None and _kmeans is not None

def recommend(title:str, top_k:int=10):
  col=resolve_columns(_df)
  idx=_title_to_idx.get(title)
  if idx is None:
    lower={k.lower():v for k,v in _title_to_idx.items()}
    idx=lower.get(title.lower())
    if idx is None: raise KeyError('Title not found')
  cluster=int(_df.iloc[idx]['cluster'])
  same=np.where(_df['cluster'].values==cluster)[0]
  sims=cosine_similarity(_X[idx], _X[same]).ravel()
  order=np.argsort(-sims)
  ranked=[]
  for j in order:
    gi=int(same[j])
    if gi==idx: continue
    ranked.append((gi,float(sims[j])))
    if len(ranked)>=top_k: break
  res=[]
  for gi,score in ranked:
    row=_df.iloc[gi]
    res.append({'title':str(row[col['title']]),'main_genre':str(row[col['main_genre']]),'side_genre':str(row[col['side_genre']]),'rating':None if pd.isna(row.get(col['rating'])) else float(row.get(col['rating'])),'runtime':None if pd.isna(row.get(col['runtime'])) else float(row.get(col['runtime'])),'score':round(score,4)})
  return res

app=Flask(__name__)

@app.route('/')
def index():
  data_present=DATA_FILE.exists()
  k=int(os.getenv('KMEANS_K', 180))
  try:
    if data_present: build_or_load_artifacts(k)
  except Exception as e:
    return render_template('index.html', data_present=data_present, error=str(e))
  return render_template('index.html', data_present=data_present, error=None)

@app.get('/titles')
def titles():
  if not DATA_FILE.exists(): return jsonify([])
  if not ready(): build_or_load_artifacts(int(os.getenv('KMEANS_K',180)))
  col=resolve_columns(_df); return jsonify(_df[col['title']].tolist())

@app.post('/recommend')
def recommend_api():
  if not DATA_FILE.exists(): return jsonify({'error':'Dataset not found. Place IMDB_All_Genres_etf_clean1.csv under ./data'}),400
  if not ready(): build_or_load_artifacts(int(os.getenv('KMEANS_K',180)))
  payload=request.get_json(force=True, silent=True) or {}
  title=(payload.get('title') or '').strip(); k=int(payload.get('k',10))
  if not title: return jsonify({'error':"Missing 'title'"}),400
  try:
    results=recommend(title,k); return jsonify({'query':title,'k':k,'results':results})
  except KeyError:
    return jsonify({'error':'Title not found in dataset'}),404
  except Exception as e:
    return jsonify({'error':str(e)}),500

@app.get('/health')
def health(): return jsonify({'ok':True})

if __name__=='__main__':
  app.run(debug=True, port=5000)
