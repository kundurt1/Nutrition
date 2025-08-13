import React, { useState } from 'react';
import {
    View,
    Text,
    ScrollView,
    TextInput,
    TouchableOpacity,
    SafeAreaView,
    StyleSheet,
    Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { colors } from '../styles/colors';
import { Recipe, RecipeStackParamList } from '../types/navigation';

type GenerateRecipeScreenNavigationProp = StackNavigationProp<
    RecipeStackParamList,
    'GenerateRecipe'
>;

const GenerateRecipeScreen = () => {
    const navigation = useNavigation<GenerateRecipeScreenNavigationProp>();
    const [recipeTitle, setRecipeTitle] = useState('');
    const [mealType, setMealType] = useState('Quick Pasta Dishes');
    const [loading, setLoading] = useState(false);
    const [recipes, setRecipes] = useState<Recipe[]>([]);

    const mealTypes = [
        'Quick Pasta Dishes',
        'Breakfast',
        'Lunch',
        'Dinner',
        'Snacks',
        'High Protein',
        'Low Carb',
        'Vegetarian'
    ];

    const mockRecipes: Recipe[] = [
        {
            id: 1,
            recipe_name: 'Chicken Pesto Pasta',
            ingredients: 'Chicken breast, Pesto sauce, Pasta, Parmesan cheese',
            instructions: '1. Cook pasta according to package directions\n2. Season and cook chicken\n3. Mix with pesto and cheese',
            macros: 'Calories: 520, Protein: 35g, Carbs: 45g, Fat: 22g'
        },
        {
            id: 2,
            recipe_name: 'Chicken Mushroom Pasta',
            ingredients: 'Chicken breast, Mushrooms, Pasta, Cream sauce',
            instructions: '1. Cook pasta\n2. Sauté chicken and mushrooms\n3. Combine with cream sauce',
            macros: 'Calories: 480, Protein: 32g, Carbs: 42g, Fat: 18g'
        },
        {
            id: 3,
            recipe_name: 'Taco Pasta',
            ingredients: 'Ground beef, Taco seasoning, Pasta, Cheese, Salsa',
            instructions: '1. Brown ground beef with taco seasoning\n2. Cook pasta\n3. Mix together with cheese and salsa',
            macros: 'Calories: 550, Protein: 30g, Carbs: 48g, Fat: 25g'
        }
    ];

    const handleGenerate = async () => {
        if (!recipeTitle.trim()) {
            Alert.alert('Error', 'Please enter a recipe title');
            return;
        }

        setLoading(true);

        // Simulate API call
        setTimeout(() => {
            setRecipes(mockRecipes);
            setLoading(false);
        }, 2000);
    };

    const MealTypeSelector = () => (
        <View style={styles.mealTypeContainer}>
            <Text style={styles.sectionTitle}>Type of Meals</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.mealTypeScroll}>
                {mealTypes.map((type) => (
                    <TouchableOpacity
                        key={type}
                        style={[
                            styles.mealTypeChip,
                            mealType === type && styles.mealTypeChipActive
                        ]}
                        onPress={() => setMealType(type)}
                    >
                        <Text style={[
                            styles.mealTypeText,
                            mealType === type && styles.mealTypeTextActive
                        ]}>
                            {type}
                        </Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>
        </View>
    );

    const RecipeCard = ({ recipe }: { recipe: Recipe }) => (
        <TouchableOpacity
            style={styles.recipeCard}
            onPress={() => navigation.navigate('Instruction', { recipe })}
        >
            <View style={styles.recipeHeader}>
                <Text style={styles.recipeName}>{recipe.recipe_name}</Text>
                <TouchableOpacity style={styles.regenerateButton}>
                    <Text style={styles.regenerateText}>Regenerate</Text>
                </TouchableOpacity>
            </View>

            <Text style={styles.recipeIngredients}>
                Ingredients: {recipe.ingredients}
            </Text>

            <Text style={styles.recipeMacros}>{recipe.macros}</Text>

            <View style={styles.recipeFooter}>
                <TouchableOpacity style={styles.addToGroceryButton}>
                    <Text style={styles.addToGroceryText}>Add to Grocery List</Text>
                </TouchableOpacity>
            </View>
        </TouchableOpacity>
    );

    return (
        <SafeAreaView style={styles.container}>
            <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
                {/* Header */}
                <View style={styles.header}>
                    <Text style={styles.headerTitle}>Generate Recipes</Text>
                </View>

                {/* Input Section */}
                <View style={styles.inputSection}>
                    <Text style={styles.inputLabel}>Generate 3 Recipes</Text>
                    <MealTypeSelector />

                    <TextInput
                        style={styles.textInput}
                        value={recipeTitle}
                        onChangeText={setRecipeTitle}
                        placeholder="eg. Quick Pasta Dishes"
                        multiline
                    />

                    <TouchableOpacity
                        style={[styles.generateButton, loading && styles.generateButtonDisabled]}
                        onPress={handleGenerate}
                        disabled={loading}
                    >
                        <Text style={styles.generateButtonText}>
                            {loading ? 'Generating...' : 'Generate Grocery List'}
                        </Text>
                    </TouchableOpacity>
                </View>

                {/* Results Section */}
                {recipes.length > 0 && (
                    <View style={styles.resultsSection}>
                        {recipes.map((recipe) => (
                            <RecipeCard key={recipe.id} recipe={recipe} />
                        ))}
                    </View>
                )}
            </ScrollView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    scrollView: {
        flex: 1,
        paddingHorizontal: 16,
    },
    header: {
        paddingTop: 20,
        paddingBottom: 24,
        alignItems: 'center',
    },
    headerTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: colors.text,
    },
    inputSection: {
        backgroundColor: colors.cardBackground,
        borderRadius: 16,
        padding: 20,
        marginBottom: 24,
        shadowColor: '#000',
        shadowOffset: {
            width: 0,
            height: 2,
        },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 2,
    },
    inputLabel: {
        fontSize: 18,
        fontWeight: '600',
        color: colors.text,
        marginBottom: 16,
    },
    sectionTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: colors.text,
        marginBottom: 12,
    },
    mealTypeContainer: {
        marginBottom: 20,
    },
    mealTypeScroll: {
        flexDirection: 'row',
    },
    mealTypeChip: {
        paddingHorizontal: 16,
        paddingVertical: 8,
        marginRight: 8,
        backgroundColor: colors.surfaceLight,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: colors.border,
    },
    mealTypeChipActive: {
        backgroundColor: colors.primary,
        borderColor: colors.primary,
    },
    mealTypeText: {
        fontSize: 14,
        color: colors.textSecondary,
        fontWeight: '500',
    },
    mealTypeTextActive: {
        color: colors.textInverse,
    },
    textInput: {
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: 12,
        padding: 16,
        fontSize: 16,
        color: colors.text,
        backgroundColor: colors.background,
        minHeight: 80,
        textAlignVertical: 'top',
        marginBottom: 20,
    },
    generateButton: {
        backgroundColor: colors.secondary,
        borderRadius: 12,
        paddingVertical: 16,
        alignItems: 'center',
    },
    generateButtonDisabled: {
        opacity: 0.6,
    },
    generateButtonText: {
        color: colors.textInverse,
        fontSize: 16,
        fontWeight: '600',
    },
    resultsSection: {
        marginBottom: 32,
    },
    recipeCard: {
        backgroundColor: colors.cardBackground,
        borderRadius: 16,
        padding: 20,
        marginBottom: 16,
        shadowColor: '#000',
        shadowOffset: {
            width: 0,
            height: 2,
        },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 2,
    },
    recipeHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    recipeName: {
        fontSize: 18,
        fontWeight: 'bold',
        color: colors.text,
        flex: 1,
    },
    regenerateButton: {
        backgroundColor: colors.error,
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 16,
    },
    regenerateText: {
        color: colors.textInverse,
        fontSize: 12,
        fontWeight: '500',
    },
    recipeIngredients: {
        fontSize: 14,
        color: colors.textSecondary,
        marginBottom: 8,
        lineHeight: 20,
    },
    recipeMacros: {
        fontSize: 14,
        color: colors.textSecondary,
        marginBottom: 16,
    },
    recipeFooter: {
        alignItems: 'center',
    },
    addToGroceryButton: {
        backgroundColor: colors.primary,
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 20,
    },
    addToGroceryText: {
        color: colors.textInverse,
        fontSize: 14,
        fontWeight: '600',
    },
});

export default GenerateRecipeScreen;