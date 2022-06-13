import numpy as np
import pandas as pd
import geopandas as gpd
import datetime as dt
import pytz
from bokeh.models import ColumnDataSource, CDSView, BooleanFilter

import config as cfg


class DataProvider(object):
    RAW_COLS = ['Accident_Index', 'Latitude', 'Longitude', 'Accident_Severity', 'Number_of_Vehicles', 'Number_of_Casualties', 'Weather_Conditions', 'Date', 'Time']
    COLS = [ 'x', 'y', 'Accident_Severity', 'Number_of_Vehicles','Number_of_Casualties' ,'datetime']
    HOSPITAL_COLS = [ 'x', 'y', 'OrganisationName']
    
    #add a colormap to signal te severity of the accident
    colormap={"1":"darkred",
               "2":"saddlebrown",
               "3":"orange"}
    
    Severitymap={"1":"Severe",
               "2":"Medium",
               "3":"Minor"}

    def __init__(self):
        
        self.df_acc = pd.read_csv('visdat-heroku/data/accidents_2005_5000lines.csv',usecols=DataProvider.RAW_COLS)
        self.df_acc.loc[:, 'dt'] = self.df_acc.Date.str.cat(self.df_acc.Time, sep=' ', na_rep='00:00')
        self.df_acc.loc[:, 'datetime'] = pd.to_datetime(self.df_acc.dt, dayfirst=True) #dayfirst -> DD/MM/YY, default is MM/DD/YY

        #Enlarge the value in order toget bigger radius value on the map
        self.df_acc.loc[:, 'Casualties3']=(self.df_acc.Number_of_Casualties)*3 
        self.COLS.append('Casualties3')

        #add colors and verbal severity to map severity of accidents
        self.df_acc.loc[:,'color']=[self.colormap[s] for s in self.df_acc.Accident_Severity.astype('str')]
        self.df_acc.loc[:,'Verbal_severity']=[self.Severitymap[s] for s in self.df_acc.Accident_Severity.astype('str')]
        
        self.COLS.append('color')
        self.COLS.append('Verbal_severity')

        self.hospitals_df=pd.DataFrame(columns=np.arange(0,22))
        with open('visdat-heroku/data/UK_Hospital.csv', "r", encoding="cp1252") as f:
            for line in f:
                x = np.asarray(line.split('¬'))
                df2 = pd.DataFrame(np.expand_dims(x,axis=1).T)
                self.hospitals_df = self.hospitals_df.append(df2,ignore_index=True)
        self.hospitals_df.columns= self.hospitals_df.iloc[0].values      
        self.hospitals_df = self.hospitals_df.drop([0])
        
        x, y = DataProvider.reproject(self.hospitals_df[["Longitude", "Latitude"]],
              from_crs="epsg:4269",
              to_crs="epsg:3857")
        self.hospitals_df["x"] = x
        self.hospitals_df["y"] = y
        
        #print(self.hospitals_df.iloc[1])

        
        # Calculation for the distance from hospital
        x1, y1 = DataProvider.reproject(self.df_acc[["Longitude", "Latitude"]])
        
        self.sqr_diff_x=np.square(np.subtract(np.expand_dims(x1,-1),np.expand_dims(self.hospitals_df.x,0)))
        self.sqr_diff_y=np.square(np.subtract(np.expand_dims(y1,-1),np.expand_dims(self.hospitals_df.y,0)))
        print('shapes of diff x and y :{}{}'.format(self.sqr_diff_x.shape,self.sqr_diff_y.shape))
        self.distance=np.round(np.sqrt(np.add(self.sqr_diff_x,self.sqr_diff_y))/1000,2)
        print(pd.DataFrame(self.distance).min(axis=1)[:5])
        self.df_acc['closest_hospital_distance']=pd.DataFrame(self.distance).min(axis=1).astype('str')
        #print('shapes of closest hospital and df_acc :{}{}'.format(self.closest_hospital_name.shape,self.df_acc.shape))
        self.df_acc['closest_hospital_name']=self.hospitals_df.loc[np.argmin(self.distance,axis=1),'OrganisationName'].values
        self.COLS.append('closest_hospital_distance')
        self.COLS.append('closest_hospital_name')

        # Preparing containers
        self.tz = pytz.timezone("Europe/London")
        self.data = pd.DataFrame(columns=DataProvider.COLS)
        self.data_ds = ColumnDataSource(data={cl: [] for cl in DataProvider.COLS})
        self.data_view = CDSView(filters=[], source=self.data_ds)
        self.type_stats_ds = ColumnDataSource(data={"Accident_Severity": [], "counts": []})
        self.dispatch_types = []
        self.data_ds_hospitals = ColumnDataSource(data={cl: [] for cl in DataProvider.HOSPITAL_COLS})
        self.data_view_hospitals = CDSView(filters=[], source=self.data_ds_hospitals)
        
        #fill the hospital datasource (because is constant)      
        self.data_ds_hospitals.data = self.hospitals_df[DataProvider.HOSPITAL_COLS].to_dict(orient="list")
        #self.data_ds_hospitals.stream(self.hospitals_df[DataProvider.HOSPITAL_COLS].to_dict(orient="list"))

        self.start_date = dt.datetime.strptime(u'04/01/2005', "%d/%m/%Y")  #datetime.datetime(2005, 1, 4, 0, 0)
        self.end_date = dt.datetime.strptime(u'09/01/2005', "%d/%m/%Y")
        self.start_casualties = 0
        self.end_casualties = self.get_max_casualties()
        
        self.update_date_filter()
        self.update_casualities_filter()
        self.update_main_data()
        self.update_stats()
        
        
    def update_main_data(self):
        filters = self.time_filter & self.casualities_filter
        data = self.df_acc[filters].copy()
        data.dropna(subset=["Longitude", "Latitude"], inplace=True)
        if not data.empty:
            # Handling geometry
            x, y = DataProvider.reproject(data[["Longitude", "Latitude"]])
            data["x"] = x
            data["y"] = y
            self.data = data[DataProvider.COLS]
            self.data_ds.data = data[DataProvider.COLS].to_dict(orient="list")
        else:
            self.data_ds.stream({cl: [] for cl in DataProvider.COLS})
        
    def get_boundary_dates(self):
        sorted = np.sort(self.df_acc.datetime.values)
        return np.array([pd.to_datetime(sorted[1]).strftime('%d/%m/%Y') , pd.to_datetime(sorted[-1]).strftime('%d/%m/%Y')])

    def get_max_casualties(self):
        sorted = np.sort(self.df_acc.Number_of_Casualties.values)
        return sorted[-1]

    def set_date(self, new_dates_tuple):
        """Update number of recent hours and corresponding views."""
        print("in set_date")
        print(new_dates_tuple)
        self.start_date = dt.datetime.fromtimestamp(new_dates_tuple[0] / 1e3) 
        self.end_date = dt.datetime.fromtimestamp(new_dates_tuple[1] / 1e3) 
        self.update_date_filter()
        self.update_stats()
        self.update_main_data()
        
    def set_casualties(self, new_casualties_tuple):
        """Update number of recent hours and corresponding views."""
        print("in set_casualties")
        print(new_casualties_tuple)
        self.start_casualties = new_casualties_tuple[0] 
        self.end_casualties = new_casualties_tuple[1]
        self.update_casualities_filter()
        self.update_stats()
        self.update_main_data()         

    def update_stats(self):
        print("in update_stats")
        filters = self.time_filter & self.casualities_filter
        type_counts = (self.df_acc.loc[filters, "Accident_Severity"]
                       .value_counts(ascending=False)
                       .to_frame()
                       .reset_index()
                       .rename({"Accident_Severity": "counts", "index": "Accident_Severity"}, axis=1))

        print(type_counts)

        
        type_counts['color']=[self.colormap[s] for s in type_counts.Accident_Severity.astype('str')]
        #type_counts.Accident_Severity=type_counts.Accident_Severity.astype('str').replace(self.Severitymap)

        tmp = type_counts.to_dict(orient="list")
        tmp['Accident_Severity'] = [str(item) for item in tmp['Accident_Severity']]
        tmp['Accident_Severity']=[self.Severitymap[sevirty] for sevirty in tmp['Accident_Severity']]
        self.type_stats_ds.data = tmp
        self.dispatch_types = [str(item) for item in tmp["Accident_Severity"]]# on my version of pandas i Get an Attribute error ''Series' object has no attribute 'to_list''
        print(tmp)

    def update_date_filter(self):
        print("in update_filter")
        """Get mask to filter record by date."""
        self.time_filter = (self.df_acc.datetime>self.start_date) & (self.df_acc.datetime<self.end_date)

    def update_casualities_filter(self):
        print("in update_casualities_filter")
        """Get mask to filter record by casualties."""
        self.casualities_filter = (self.df_acc.Number_of_Casualties>=self.start_casualties) & (self.df_acc.Number_of_Casualties<self.end_casualties)


    @staticmethod
    def reproject(data,
                  x_col="Longitude",
                  y_col="Latitude",
                  from_crs=cfg.DATA_CRS,
                  to_crs=cfg.PLOT_CRS):
        """Transform coordinates from `from_crs` coordinates to `to_crs`."""

        coords = data[[x_col, y_col]]
        coords[x_col] = pd.to_numeric(coords[x_col])
        coords[y_col] = pd.to_numeric(coords[y_col])

        geometry = gpd.points_from_xy(coords[x_col], coords[y_col])
        coords = gpd.GeoDataFrame(coords,
                                  geometry=geometry,
                                  crs={"init": from_crs})

        coords = coords.to_crs({"init": to_crs})
        return coords.geometry.x, coords.geometry.y