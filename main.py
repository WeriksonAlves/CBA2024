"""
Research Line: Classification of gestures for vehicle control in inspection routines
Author: Wérikson Alves
Initial Date: 25/04/2024  => Final Date: /07/2024

...............................................................................................
Description
    Operation mode:
        Build:     Creates a new database and saves it in json format
        Recognize: Load the database, create the classifier and classify the actions

    Operation stage:
        0 - Processes the image and analyzes the operator's hand
        1 - Processes the image and analyzes the operator's body
        2 - Reduces the dimensionality of the data
        3 - Updates and save the database
        4 - Performs classification from kMeans
...............................................................................................
""" 

import cv2
import numpy as np
import os
import mediapipe as mp

from Classes import *
from sklearn.neighbors import KNeighborsClassifier

class GestureRecognitionSystem:
    def __init__(self):
        # Operation mode
        self.list_mode = ['B', 'V', 'RT']  # "Build", "Validate" or "Real_Time"
        self.mode = self.list_mode[2]

        # Data input
        self.cap_RS = cv2.VideoCapture(0) # Intel RealSense
        self.cap_B = cv2.VideoCapture(2) # Bebop
        self.fps = 10
        
        # "Build"
        self.database = {'F': [], 'I': [], 'L': [], 'P': [], 'T': []}
        self.file_name_build = "Datasets\DataBase_(5-10)_Werikson_11.json"
        self.max_num_gest = 50
        self.dist = 0.025
        self.length = 15
        
        # "Validate"
        self.proportion = 0.7
        self.files_name = [
            'Datasets\DataBase_(5-10)_Guilherme.json',
            'Datasets\DataBase_(5-10)_Hiago.json',
            'Datasets\DataBase_(5-10)_Lucas.json',
            'Datasets\DataBase_(5-10)_Mateus.json',
            'Datasets\DataBase_(5-10)_Thayron.json',
            'Datasets\DataBase_(5-10)_Werikson_1.json',
            'Datasets\DataBase_(5-10)_Werikson_2.json',
            'Datasets\DataBase_(5-10)_Werikson_3.json',
            'Datasets\DataBase_(5-10)_Werikson_4.json',
            'Datasets\DataBase_(5-10)_Werikson_5.json',
            'Datasets\DataBase_(5-10)_Werikson_6.json',
            'Datasets\DataBase_(5-10)_Werikson_7.json',
            'Datasets\DataBase_(5-10)_Werikson_8.json',
            'Datasets\DataBase_(5-10)_Werikson_9.json',
            'Datasets\DataBase_(5-10)_Werikson_10.json'
        ]
        self.k = int(np.round(np.sqrt(int(len(self.files_name) * 10 * 5 * self.proportion))))
        self.file_name_val = f"Results\C5_S45_p{int(10*self.proportion)}{int(10*(1-self.proportion))}_k{self.k}_Val99"
        
        
        # "Real_Time"
        self.file_name_realtime = f"Results\C5_S45_p{int(10*self.proportion)}{int(10*(1-self.proportion))}_k{self.k}_rt00"
        
        # Initialize objects
        self.pdi = YoloProcessor('yolov8n-pose.pt')
        self.file = FileHandler()
        self.data = DataProcessor()
        self.t_func = TimeFunctions()
        self.gest = GestureAnalyzer()
        self.classifier = KNN(
            KNeighborsClassifier(
                n_neighbors=self.k, 
                algorithm='auto', 
                weights='uniform'
                )
            )
        self.feature = HolisticProcessor(
            mp.solutions.hands.Hands(
                static_image_mode=False, 
                max_num_hands=1, 
                model_complexity=1, 
                min_detection_confidence=0.75, 
                min_tracking_confidence=0.75
                ),
            mp.solutions.pose.Pose(
                static_image_mode=False, 
                model_complexity=1, 
                smooth_landmarks=True, 
                enable_segmentation=False, 
                smooth_segmentation=True, 
                min_detection_confidence=0.75, 
                min_tracking_confidence=0.75
                )
            )
        
        # Simulation variables
        self.stage = 0
        self.num_gest = 0
        self.dist_virtual_point = 1
        self.hands_results = None
        self.pose_results = None
        self.time_gesture = None
        self.time_action = None
        self.y_val = None
        self.frame_captured = None
        self.y_predict = []
        self.time_classifier = []
        
        # Storage variables
        self.current_folder = os.path.dirname(__file__)
        self.hand_history, _, self.wrists_history, self.sample = self.data.initialize_data(self.dist, self.length)
    
    def read_image(self) -> bool:
        """
        The function `read_image` reads an image from a camera capture device and returns a success flag
        along with the captured frame.
        """
        success, self.frame_captured = self.cap_RS.read()
        if not success: 
            print(f"Image capture error.")
        return success
    
    def image_processing(self) -> bool:
        """
        This function processes captured frames to detect and track an operator, extract features, and
        display the results.
        """
        try:
            # Find a person and build a bounding box around them, tracking them throughout the
            # experiment.
            results_people = self.pdi.find_people(self.frame_captured)
            results_identifies = self.pdi.identify_operator(results_people)
            
            # Cut out the bounding box for another image.
            projected_window = self.pdi.track_operator(results_people, results_identifies, self.frame_captured)
            
            # Finds the operator's hand(s) and body
            self.hands_results, self.pose_results = self.feature.find_features(projected_window)
            
            # Draws the operator's hand(s) and body
            frame_results = self.feature.draw_features(projected_window, self.hands_results, self.pose_results)
            
            # Shows the skeleton formed on the body, and indicates which gesture is being 
            # performed at the moment.
            if self.mode == 'B':
                cv2.putText(frame_results, f"S{self.stage} N{self.num_gest+1}: {self.y_val[self.num_gest]} D{self.dist_virtual_point:.3f}" , (25,25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1, cv2.LINE_AA)
            elif self.mode == 'RT':
                cv2.putText(frame_results, f"S{self.stage} D{self.dist_virtual_point:.3f}" , (25,25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1, cv2.LINE_AA)
            cv2.imshow('RealSense Camera', frame_results)
            return  True
        except Exception as e:
            print(f"E1 - Error during operator detection, tracking or feature extraction: {e}")
            cv2.imshow('RealSense Camera', cv2.flip(self.frame_captured,1))
            self.hand_history = np.concatenate((self.hand_history, np.array([self.hand_history[-1]])), axis=0)
            self.wrists_history = np.concatenate((self.wrists_history, np.array([self.wrists_history[-1]])), axis=0)
            return False
    
    def extract_features(self) -> None:
        """
        The function `extract_features` processes hand and pose data to track specific joints and
        trigger gestures based on proximity criteria.
        """
        if self.stage == 0:
            try:
                # Tracks the fingertips of the left hand and centers them in relation to the center
                # of the hand.
                hand_ref = np.tile(self.gest.calculate_ref_pose(self.hands_results.multi_hand_landmarks[0], self.sample['joints_trigger_reference']), len(self.sample['joints_trigger']))
                hand_pose = [FeatureExtractor.calculate_joint_xy(self.hands_results.multi_hand_landmarks[0], marker) for marker in self.sample['joints_trigger']]
                hand_center = np.array([np.array(hand_pose).flatten() - hand_ref])
                self.hand_history = np.concatenate((self.hand_history, hand_center), axis=0)
            except:
                # If this is not possible, repeat the last line of the history.
                self.hand_history = np.concatenate((self.hand_history, np.array([self.hand_history[-1]])), axis=0)
            
            # Check that the fingertips are close together, if they are less than "dist" the 
            # trigger starts and the gesture begins.
            _, self.hand_history, self.dist_virtual_point = self.gest.check_trigger_enabled(self.hand_history, self.sample['par_trigger_length'], self.sample['par_trigger_dist'])
            if self.dist_virtual_point < self.sample['par_trigger_dist']:
                self.stage = 1
                self.dist_virtual_point = 1
                self.time_gesture = self.t_func.tic()
                self.time_action = self.t_func.tic()
        elif self.stage == 1:
            try:
                # Tracks the operator's wrists throughout the action
                track_ref = np.tile(self.gest.calculate_ref_pose(self.pose_results.pose_landmarks, self.sample['joints_tracked_reference'], 3), len(self.sample['joints_tracked']))
                track_pose = [FeatureExtractor.calculate_joint_xyz(self.pose_results.pose_landmarks, marker) for marker in self.sample['joints_tracked']]
                track_center = np.array([np.array(track_pose).flatten() - track_ref])
                self.wrists_history = np.concatenate((self.wrists_history, track_center), axis=0)
            except:
                # If this is not possible, repeat the last line of the history.
                self.wrists_history = np.concatenate((self.wrists_history, np.array([self.wrists_history[-1]])), axis=0)
            
            # Evaluates whether the execution time of a gesture has been completed
            if self.t_func.toc(self.time_action) > 4:
                self.stage = 2
                self.sample['time_gest'] = self.t_func.toc(self.time_gesture)
                self.t_classifier = self.t_func.tic()
    
    def process_reduction(self) -> None:
        """
        The function `process_reduction` removes the zero's line from a matrix, applies filters, and
        reduces the matrix to a 6x6 matrix based on certain conditions.
        """
        # Remove the zero's line
        self.wrists_history = self.wrists_history[1:]
        
        # Test the use of filters before applying pca
        
        # Reduces to a 6x6 matrix 
        self.sample['data_reduce_dim'] = np.dot(self.wrists_history.T, self.wrists_history)
    
    def update_database(self) -> bool:
        """
        This function updates a database with sample data and saves it in JSON format.
        
        Note: Exclusive function for database construction operating mode.
        """
        # Updates the sample
        self.sample['data_pose_track'] = self.wrists_history
        self.sample['answer_predict'] = self.y_val[self.num_gest]
        
        # Updates the database
        self.database[str(self.y_val[self.num_gest])].append(self.sample)
        
        # Save the database in JSON format
        self.file.save_database(self.sample, self.database, os.path.join(self.current_folder, self.file_name_build))
        
        # Resets sample data variables to default values
        self.hand_history, _, self.wrists_history, self.sample = self.data.initialize_data(self.dist, self.length)
        
        # Indicates the next gesture and returns to the image processing step
        self.num_gest += 1
        if self.num_gest == self.max_num_gest: 
            return True
        else: 
            return False
    
    def classify_gestures(self) -> None:
        """
        This function classifies gestures based on the stage and mode, updating predictions and
        resetting sample data variables accordingly.
        
        Note: Exclusive function for Real-Time operating mode
        """
        # Classifies the action performed
        self.y_predict.append(self.classifier.my_predict(self.sample['data_reduce_dim']))
        self.time_classifier.append(self.t_func.toc(self.t_classifier))
        print(f"The gesture performed belongs to class {self.y_predict[-1]} and took {self.time_classifier[-1]} to be classified. The total time taken for the action was {self.time_classifier[-1] + self.sample['time_gest']}. The action taken belongs to the class: ")
        
        # Resets sample data variables to default values
        self.hand_history, _, self.wrists_history, self.sample = self.data.initialize_data(self.dist, self.length)
    
    def run(self):
        if self.mode == 'B':
            self.target_names, self.y_val = self.file.initialize_database(self.database)
            loop = True
        elif self.mode == 'RT':
            x_train, y_train, _, _ = self.file.load_database(self.current_folder, self.files_name, self.proportion)
            self.classifier.fit(x_train, y_train)
            loop = True
        elif  self.mode == 'V':
            x_train, y_train, x_val, self.y_val = self.file.load_database(self.current_folder, self.files_name, self.proportion)
            self.classifier.fit(x_train, y_train)
            self.y_predict, self.time_classifier = self.classifier.validate(x_val)
            self.target_names, _ = self.file.initialize_database(self.database)
            self.file.save_results(self.y_val, self.y_predict, self.time_classifier, self.target_names, os.path.join(self.current_folder, self.file_name_val))
            loop = False
        else:
            print(f"Operation mode invalid!")
            loop = False
                
        t_frame = self.t_func.tic()
        while loop:
            # Sampling window
            if self.t_func.toc(t_frame) > 1 / self.fps:
                t_frame = self.t_func.tic()
                
                # Stop condition
                if (cv2.waitKey(10) & 0xFF == ord("q")) or ((self.num_gest == self.max_num_gest) and (self.mode == "B")): break
                
                if (self.stage == 0 or self.stage == 1) and (self.mode == 'B' or self.mode == 'RT'):
                    if not self.read_image(): 
                        continue
                    failure = self.image_processing()
                    if not failure: 
                        continue
                    self.extract_features()
                elif self.stage == 2 and (self.mode == 'B' or self.mode == 'RT'):
                    self.process_reduction()
                    if self.mode == "B": 
                        self.stage = 3
                    elif self.mode == "RT": 
                        self.stage = 4
                elif self.stage == 3 and self.mode == 'B':
                    end_simulation = self.update_database()
                    if end_simulation: 
                        loop = False
                    self.stage = 0
                elif self.stage == 4 and self.mode == 'RT':
                    self.classify_gestures()
                    self.stage = 0

        self.cap_RS.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    grs = GestureRecognitionSystem()

    grs.run()
