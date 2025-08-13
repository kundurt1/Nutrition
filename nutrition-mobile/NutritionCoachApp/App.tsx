import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { StatusBar } from 'react-native';
import { AuthProvider, useAuth } from './src/contexts/AuthContext';
import AuthScreen from './src/screens/AuthScreen';
import MainTabNavigator from './src/navigation/MainTabNavigator';
import { colors } from './src/styles/colors';
import { RootStackParamList } from './src/types/navigation';

const Stack = createStackNavigator<RootStackParamList>();

const AppNavigator = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return null; // You could add a loading screen here
  }

  return (
      <NavigationContainer>
        <StatusBar barStyle="dark-content" backgroundColor={colors.background} />
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          {user ? (
              <Stack.Screen name="Main" component={MainTabNavigator} />
          ) : (
              <Stack.Screen name="Auth" component={AuthScreen} />
          )}
        </Stack.Navigator>
      </NavigationContainer>
  );
};

export default function App() {
  return (
      <AuthProvider>
        <AppNavigator />
      </AuthProvider>
  );
}