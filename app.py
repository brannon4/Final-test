import io, re, os, hmac
from urllib.parse import quote_plus
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Pick & Profit MA',page_icon='🚗',layout='wide')
# Fail closed: never show inventory, uploaded comps, or exports without authentication.
# Set APP_PASSWORD in the cloud host's encrypted environment settings.
password = os.environ.get('APP_PASSWORD', '')
if not password:
    st.error('Private access is not configured. The owner must set APP_PASSWORD in the hosting environment.')
    st.stop()

if not st.session_state.get('authenticated', False):
    st.title('🔒 Pick & Profit MA')
    st.caption('Private junkyard resale research · Owner sign-in')
    with st.form('owner_login'):
        entered = st.text_input('Password', type='password')
        submitted = st.form_submit_button('Unlock app', use_container_width=True)
    if submitted:
        if hmac.compare_digest(entered.encode(), password.encode()):
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error('Incorrect password')
    st.stop()

st.markdown("""<style>
@media(max-width: 700px) {
  .block-container {padding: 1rem .7rem 4rem;}
  h1 {font-size: 1.7rem !important;}
  [data-testid="stDataFrame"] {max-width: 100%;}
}
</style>""", unsafe_allow_html=True)
with st.sidebar:
    if st.button('🔒 Sign out', use_container_width=True):
        st.session_state.clear()
        st.rerun()
st.title('🚗 Pick & Profit | Massachusetts')
st.caption('Junkyard inventory → candidate parts → verified sold comps → estimated profit. No invented sales data.')

PARTS = {
 'Honda Element':['OEM roof rack crossbars','rear cargo floor panel','climate control panel','factory radio','sun visor pair'],
 'Ford F-150':['OEM LED tail lamp','power mirror assembly','climate control panel','SYNC radio screen','window master switch'],
 'BMW 328i':['iDrive controller','climate control panel','factory amplifier','headlight assembly','window switch'],
 'Ford Explorer':['SYNC infotainment screen','LED tail lamp','power mirror assembly','climate control panel','factory amplifier'],
 'Toyota Prius':['instrument cluster','multi-function display','climate control panel','headlight assembly'],
 'Honda Accord':['climate control panel','factory navigation display','power mirror assembly','factory amplifier'],
}
GENERAL=['climate control panel','OEM audio amplifier','factory navigation screen','headlight assembly','tail lamp assembly','power mirror assembly','window master switch','interior trim']
BLOCK=re.compile(r'\b(engine|transmission|differential|gearbox|transaxle)\b',re.I)

@st.cache_data
def seed():
 return pd.read_csv('sample_inventory.csv')

with st.sidebar:
 st.header('Data sources')
 st.markdown('[Springfield vehicle inventory](https://yardhound.app/?yard_id=136)')
 st.markdown('[Pick-n-Pull official inventory](https://www.picknpull.com/check-inventory/)')
 st.markdown('[Pick-n-Pull part prices](https://www.picknpull.com/part-pricing/)')
 st.markdown('[eBay Product Research help](https://www.ebay.com/help/selling/terapeak-research/terapeak-product-research?id=4853)')
 st.info('Import current inventory and actual sold comps for updated calculations. The bundled inventory is a dated sample, not live yard availability.')
 st.download_button('Inventory CSV template', 'yard,year,make,model,trim,row,vin,arrival_date,source_url\n',file_name='inventory_template.csv')
 st.download_button('Sold comps CSV template','query,sold_price,shipping_charged,sold_date,condition,source_url\n',file_name='sold_comps_template.csv')
 st.download_button('Yard price CSV template','yard,part,price\n',file_name='yard_prices_template.csv')

invfile=st.file_uploader('Upload latest yard vehicle inventory (CSV)',type='csv',key='inv')
try: inv=pd.read_csv(invfile) if invfile else seed()
except Exception as e: st.error(f'Inventory CSV error: {e}');st.stop()
for col in ['yard','year','make','model','trim','row','vin','arrival_date','source_url']:
 if col not in inv: inv[col]=''
inv=inv.fillna('')

st.subheader('1 · Cars on the lot')
if not invfile: st.warning('Showing a small, sourced Springfield inventory snapshot for demonstration. Upload a fresh inventory CSV to work from current yard data.')
yards=sorted(inv.yard.astype(str).unique())
chosen=st.multiselect('Yards',yards,default=yards)
search=st.text_input('Filter cars (make, model, year, VIN)',placeholder='e.g. 2016 Explorer')
filtered=inv[inv.yard.isin(chosen)].copy()
if search: filtered=filtered[filtered.astype(str).agg(' '.join,axis=1).str.contains(search,case=False,regex=False)]
st.metric('Matching vehicles',len(filtered))
st.dataframe(filtered[['yard','year','make','model','trim','row','vin','arrival_date']],use_container_width=True,hide_index=True)

st.subheader('2 · Part opportunity finder')
options=[]
for _,v in filtered.iterrows():
 car=f"{v['year']} {v['make']} {v['model']}".strip()
 specific=next((p for k,p in PARTS.items() if k.lower() in f"{v['make']} {v['model']}".lower()),GENERAL)
 for p in specific:
  if not BLOCK.search(p): options.append(dict(yard=v['yard'],car=car,row=v['row'],part=p,query=f'{car} {p} OEM used',vin=v['vin']))
op=pd.DataFrame(options)
if op.empty: st.info('No candidate parts for these vehicles.');st.stop()
part_search=st.text_input('Filter parts',placeholder='amplifier, climate control, mirror...')
if part_search:op=op[op.part.str.contains(part_search,case=False,regex=False)]

st.subheader('3 · Actual sold comps and junkyard prices')
compfile=st.file_uploader('Upload eBay Product Research / sold-comps CSV',type='csv',key='comps',help='Columns: query,sold_price; optional shipping_charged,sold_date,condition,source_url. Query should match the opportunity search exactly.')
pricefile=st.file_uploader('Upload yard part prices CSV',type='csv',key='prices',help='Columns: yard,part,price. Exact yard and part category names should match.')
fees=st.number_input('Estimated eBay fee (%)',min_value=0.,max_value=40.,value=13.6,step=.1)
ship=st.number_input('Shipping cost per part ($)',min_value=0.,value=15.,step=1.)
pack=st.number_input('Packing cost per part ($)',min_value=0.,value=3.,step=1.)
reserve=st.number_input('Returns/risk reserve per part ($)',min_value=0.,value=5.,step=1.)
fixed=st.number_input('Fixed transaction fee ($)',min_value=0.,value=.40,step=.05)
min_n=st.slider('Minimum sold comps for confidence',1,20,3)

comps=pd.DataFrame(columns=['query','sold_price'])
if compfile:
 try:
  comps=pd.read_csv(compfile)
  if not {'query','sold_price'}.issubset(comps.columns): raise ValueError('query and sold_price columns required')
  comps['sold_price']=pd.to_numeric(comps.sold_price,errors='coerce')
  comps=comps.dropna(subset=['sold_price'])
 except Exception as e:st.error(f'Comps CSV error: {e}');comps=pd.DataFrame(columns=['query','sold_price'])
prices=pd.DataFrame(columns=['yard','part','price'])
if pricefile:
 try:
  prices=pd.read_csv(pricefile)
  if not {'yard','part','price'}.issubset(prices.columns):raise ValueError('yard, part, price columns required')
  prices['price']=pd.to_numeric(prices.price,errors='coerce')
 except Exception as e:st.error(f'Yard prices CSV error: {e}');prices=pd.DataFrame(columns=['yard','part','price'])

if not comps.empty:
 summary=comps.groupby('query',as_index=False).agg(median_sold=('sold_price','median'),sales_count=('sold_price','size'),low_sold=('sold_price','min'),high_sold=('sold_price','max'))
 op=op.merge(summary,on='query',how='left')
else:
 for c in ['median_sold','sales_count','low_sold','high_sold']:op[c]=float('nan')
if not prices.empty:op=op.merge(prices.rename(columns={'price':'yard_cost'}),on=['yard','part'],how='left')
else:op['yard_cost']=float('nan')
op['estimated_net_profit']=op['median_sold']*(1-fees/100)-op['yard_cost']-ship-pack-reserve-fixed
op['roi_pct']=100*op['estimated_net_profit']/op['yard_cost'].replace(0,float('nan'))
op['confidence']=op.sales_count.apply(lambda n:'Verified sample' if pd.notna(n) and n>=min_n else ('Limited comps' if pd.notna(n) else 'No sold data'))
op['ebay_sold_search']=op['query'].apply(lambda q:'https://www.ebay.com/sch/i.html?_nkw='+quote_plus(q)+'&LH_Sold=1&LH_Complete=1')
op['ebay_active_search']=op['query'].apply(lambda q:'https://www.ebay.com/sch/i.html?_nkw='+quote_plus(q))

st.subheader('4 · Ranked opportunities')
verified=op.dropna(subset=['estimated_net_profit']).sort_values('estimated_net_profit',ascending=False)
if verified.empty:st.info('To show genuine profit rankings, upload BOTH sold-comps data and the yard price sheet. Until then, candidates remain research leads, not profit claims.')
else:
 st.metric('Best estimated net profit',f"${verified.iloc[0].estimated_net_profit:,.2f}")
 st.dataframe(verified[['yard','car','row','part','yard_cost','median_sold','sales_count','estimated_net_profit','roi_pct','confidence','ebay_sold_search']],use_container_width=True,hide_index=True,column_config={'ebay_sold_search':st.column_config.LinkColumn('Sold listings')})
st.caption('Estimated net excludes taxes, driving time, labor, return freight, and part defects. Matching by model/year is not proof a part fits; verify OEM part number and options.')
st.dataframe(op[['yard','car','row','part','query','ebay_sold_search','ebay_active_search']],use_container_width=True,hide_index=True,column_config={'ebay_sold_search':st.column_config.LinkColumn('Sold search'),'ebay_active_search':st.column_config.LinkColumn('Active search')})
st.download_button('Export all opportunities CSV',op.to_csv(index=False).encode(),file_name='pick_profit_opportunities.csv',mime='text/csv')
