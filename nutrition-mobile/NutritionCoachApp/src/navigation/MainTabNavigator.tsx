import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../styles/colors';
import { MainTabParamList, RecipeStackParamList } from '../types/navigation';

// Import screens
import HomeScreen from '../screens/HomeScreen';
import GenerateRecipeScreen from '../screens/GenerateRecipeScreen';
import GroceryListScreen from '../screens/GroceryListScreen';
import PreferencesScreen from '../screens/PreferencesScreen';
import InstructionScreen from '../screens/InstructionScreen';

const Tab = createBottomTabNavigator<MainTabParamList>();
const Stack = createStackNavigator<RecipeStackParamList>();

// Stack Navigator for Recipe Generation flow
const RecipeStack = () => (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="GenerateRecipe" component={GenerateRecipeScreen} />
        <Stack.Screen name="Instruction" component={InstructionScreen} />
    </Stack.Navigator>
);

const MainTabNavigator = () => {
    return (
        <Tab.Navigator
            screenOptions={({ route }) => ({
                headerShown: false,
                tabBarStyle: {
                    backgroundColor: colors.cardBackground,
                    borderTopWidth: 1,
                    borderTopColor: colors.border,
                    paddingBottom: 8,
                    paddingTop: 8,
                    height: 80,
                },
                tabBarActiveTintColor: colors.primary,
                tabBarInactiveTintColor: colors.textLight,
                tabBarLabelStyle: {
                    fontSize: 12,
                    fontWeight: '600',
                    marginTop: 4,
                },
                tabBarIcon: ({ focused, color, size }) => {
                    let iconName: keyof typeof Ionicons.glyphMap;

                    switch (route.name) {
                        case 'Home':
                            iconName = focused ? 'home' : 'home-outline';
                            break;
                        case 'Recipes':
                            iconName = focused ? 'restaurant' : 'restaurant-outline';
                            break;
                        case 'Grocery':
                            iconName = focused ? 'bag' : 'bag-outline';
                            break;
                        case 'Preferences':
                            iconName = focused ? 'settings' : 'settings-outline';
                            break;
                        default:
                            iconName = 'home-outline';
                    }

                    return <Ionicons name={iconName} size={size} color={color} />;
                },
            })}
        >
            <Tab.Screen
                name="Home"
                component={HomeScreen}
                options={{
                    title: 'Home page',
                }}
            />
            <Tab.Screen
                name="Recipes"
                component={RecipeStack}
                options={{
                    title: 'Generate Recipes',
                }}
            />
            <Tab.Screen
                name="Grocery"
                component={GroceryListScreen}
                options={{
                    title: 'Grocery List',
                }}
            />
            <Tab.Screen
                name="Preferences"
                component={PreferencesScreen}
                options={{
                    title: 'Preferences',
                }}
            />
        </Tab.Navigator>
    );
};

export default MainTabNavigator;