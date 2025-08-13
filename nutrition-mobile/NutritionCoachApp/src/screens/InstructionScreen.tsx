// src/screens/InstructionScreen.tsx
import React from 'react';
import {
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    SafeAreaView,
    StyleSheet,
} from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../styles/colors';
import { Recipe, RecipeStackParamList } from '../types/navigation';

type InstructionScreenNavigationProp = StackNavigationProp<
    RecipeStackParamList,
    'Instruction'
>;

type InstructionScreenRouteProp = RouteProp<
    RecipeStackParamList,
    'Instruction'
>;

const InstructionScreen = () => {
    const navigation = useNavigation<InstructionScreenNavigationProp>();
    const route = useRoute<InstructionScreenRouteProp>();
    const { recipe } = route.params;

    // Safely split ingredients and instructions with fallbacks
    const ingredients = recipe.ingredients ? recipe.ingredients.split(', ') : [];
    const instructions = recipe.instructions ? recipe.instructions.split('\n').filter(item => item.trim()) : [];

    return (
        <SafeAreaView style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity
                    style={styles.backButton}
                    onPress={() => navigation.goBack()}
                >
                    <Ionicons name="arrow-back" size={24} color={colors.text} />
                </TouchableOpacity>
                <Text style={styles.headerTitle}>Recipe Instruction</Text>
                <View style={styles.placeholder} />
            </View>

            <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
                {/* Recipe Card */}
                <View style={styles.recipeCard}>
                    <Text style={styles.recipeName}>{recipe.recipe_name || 'Recipe'}</Text>
                    <Text style={styles.cookingTime}>25 minutes</Text>

                    {/* Ingredients Section */}
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Ingredients</Text>
                        <View style={styles.ingredientsContainer}>
                            {ingredients.length > 0 ? (
                                ingredients.map((ingredient, index) => (
                                    <View key={index} style={styles.ingredientItem}>
                                        <View style={styles.ingredientBullet} />
                                        <Text style={styles.ingredientText}>{ingredient.trim()}</Text>
                                    </View>
                                ))
                            ) : (
                                <Text style={styles.ingredientText}>No ingredients available</Text>
                            )}
                        </View>
                    </View>

                    {/* Instructions Section */}
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Instructions</Text>
                        <View style={styles.instructionsContainer}>
                            {instructions.length > 0 ? (
                                instructions.map((instruction, index) => (
                                    <View key={index} style={styles.instructionItem}>
                                        <View style={styles.instructionNumber}>
                                            <Text style={styles.instructionNumberText}>{index + 1}</Text>
                                        </View>
                                        <Text style={styles.instructionText}>{instruction.trim()}</Text>
                                    </View>
                                ))
                            ) : (
                                <Text style={styles.instructionText}>No instructions available</Text>
                            )}
                        </View>
                    </View>

                    {/* Nutrition Info */}
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Nutrition Information</Text>
                        <Text style={styles.macrosText}>{recipe.macros || 'No nutrition data available'}</Text>
                    </View>
                </View>
            </ScrollView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        paddingVertical: 16,
        backgroundColor: colors.cardBackground,
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
    },
    backButton: {
        padding: 8,
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: colors.text,
    },
    placeholder: {
        width: 40,
    },
    scrollView: {
        flex: 1,
        paddingHorizontal: 16,
    },
    recipeCard: {
        backgroundColor: colors.cardBackground,
        borderRadius: 16,
        padding: 24,
        marginTop: 16,
        marginBottom: 32,
        shadowColor: '#000',
        shadowOffset: {
            width: 0,
            height: 2,
        },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 2,
    },
    recipeName: {
        fontSize: 24,
        fontWeight: 'bold',
        color: colors.text,
        marginBottom: 8,
        textAlign: 'center',
    },
    cookingTime: {
        fontSize: 16,
        color: colors.textSecondary,
        textAlign: 'center',
        marginBottom: 32,
    },
    section: {
        marginBottom: 32,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: colors.text,
        marginBottom: 16,
    },
    ingredientsContainer: {
        backgroundColor: colors.surfaceLight,
        borderRadius: 12,
        padding: 16,
    },
    ingredientItem: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 8,
    },
    ingredientBullet: {
        width: 6,
        height: 6,
        borderRadius: 3,
        backgroundColor: colors.primary,
        marginRight: 12,
    },
    ingredientText: {
        fontSize: 16,
        color: colors.text,
        flex: 1,
    },
    instructionsContainer: {
        backgroundColor: colors.surfaceLight,
        borderRadius: 12,
        padding: 16,
    },
    instructionItem: {
        flexDirection: 'row',
        marginBottom: 16,
    },
    instructionNumber: {
        width: 24,
        height: 24,
        borderRadius: 12,
        backgroundColor: colors.primary,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 12,
        marginTop: 2,
    },
    instructionNumberText: {
        fontSize: 12,
        fontWeight: 'bold',
        color: colors.textInverse,
    },
    instructionText: {
        fontSize: 16,
        color: colors.text,
        flex: 1,
        lineHeight: 24,
    },
    macrosText: {
        fontSize: 16,
        color: colors.textSecondary,
        backgroundColor: colors.surfaceLight,
        padding: 16,
        borderRadius: 12,
    },
});

export default InstructionScreen;