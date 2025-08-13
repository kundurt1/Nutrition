import React, { useState } from 'react';
import {
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    SafeAreaView,
    StyleSheet,
    Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '../styles/colors';

const { width } = Dimensions.get('window');

interface MacroData {
    protein: number;
    fats: number;
    carbohydrates: number;
}

interface RecentRecipe {
    id: number;
    name: string;
    time: string;
}

const HomeScreen = () => {
    const [macroData] = useState<MacroData>({
        protein: 65,
        fats: 65,
        carbohydrates: 65,
    });

    const [recentRecipes] = useState<RecentRecipe[]>([
        { id: 1, name: 'Chicken', time: '25 min' },
        { id: 2, name: 'Shrimp', time: '15 min' },
    ]);

    const MacroCircle = ({ label, percentage, color }: {
        label: string;
        percentage: number;
        color: string;
    }) => (
        <View style={styles.macroCircle}>
            <View style={[styles.circleContainer, { borderColor: color }]}>
                <Text style={styles.macroPercentage}>{percentage}%</Text>
            </View>
            <Text style={styles.macroLabel}>{label}</Text>
        </View>
    );

    const RecentRecipeCard = ({ recipe }: { recipe: RecentRecipe }) => (
        <TouchableOpacity style={styles.recipeCard}>
            <View style={styles.recipeImagePlaceholder} />
            <Text style={styles.recipeName}>{recipe.name}</Text>
        </TouchableOpacity>
    );

    return (
        <SafeAreaView style={styles.container}>
            <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
                {/* Header */}
                <View style={styles.header}>
                    <Text style={styles.headerTitle}>Home Page</Text>
                    <Text style={styles.headerSubtitle}>Daily Insights</Text>
                </View>

                {/* Macro Section */}
                <View style={styles.section}>
                    <View style={styles.macroHeader}>
                        <Text style={styles.sectionTitle}>Protein</Text>
                        <Text style={styles.sectionTitle}>Fats</Text>
                        <Text style={styles.sectionTitle}>Carbohydrates</Text>
                    </View>

                    <View style={styles.macroRow}>
                        <MacroCircle
                            label="Protein"
                            percentage={macroData.protein}
                            color={colors.secondary}
                        />
                        <MacroCircle
                            label="Fats"
                            percentage={macroData.fats}
                            color={colors.warning}
                        />
                        <MacroCircle
                            label="Carbohydrates"
                            percentage={macroData.carbohydrates}
                            color={colors.primary}
                        />
                    </View>
                </View>

                {/* Recent Recipes */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Recent Recipes</Text>
                    <View style={styles.recipeRow}>
                        {recentRecipes.map((recipe) => (
                            <RecentRecipeCard key={recipe.id} recipe={recipe} />
                        ))}
                    </View>
                </View>

                {/* Calorie Tracker */}
                <View style={styles.section}>
                    <TouchableOpacity style={styles.calorieTracker}>
                        <Text style={styles.calorieTrackerText}>Calorie Tracker</Text>
                    </TouchableOpacity>
                </View>

                {/* Bottom Navigation Buttons */}
                <View style={styles.bottomNav}>
                    <LinearGradient
                        colors={[colors.primary, colors.primaryLight]}
                        style={styles.navButton}
                    >
                        <TouchableOpacity style={styles.navButtonInner}>
                            <Text style={styles.navButtonText}>Preferences</Text>
                        </TouchableOpacity>
                    </LinearGradient>

                    <LinearGradient
                        colors={[colors.secondary, colors.secondaryLight]}
                        style={styles.navButton}
                    >
                        <TouchableOpacity style={styles.navButtonInner}>
                            <Text style={styles.navButtonText}>Generate Recipes</Text>
                        </TouchableOpacity>
                    </LinearGradient>

                    <LinearGradient
                        colors={[colors.warning, colors.accentLight]}
                        style={styles.navButton}
                    >
                        <TouchableOpacity style={styles.navButtonInner}>
                            <Text style={styles.navButtonText}>Grocery List</Text>
                        </TouchableOpacity>
                    </LinearGradient>
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
        marginBottom: 4,
    },
    headerSubtitle: {
        fontSize: 16,
        color: colors.textSecondary,
    },
    section: {
        marginBottom: 32,
    },
    sectionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: colors.text,
        marginBottom: 16,
    },
    macroHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 16,
    },
    macroRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    macroCircle: {
        alignItems: 'center',
        flex: 1,
    },
    circleContainer: {
        width: 80,
        height: 80,
        borderRadius: 40,
        borderWidth: 4,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: colors.cardBackground,
        marginBottom: 8,
    },
    macroPercentage: {
        fontSize: 18,
        fontWeight: 'bold',
        color: colors.text,
    },
    macroLabel: {
        fontSize: 12,
        color: colors.textSecondary,
        textAlign: 'center',
    },
    recipeRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
    },
    recipeCard: {
        flex: 1,
        backgroundColor: colors.cardBackground,
        borderRadius: 12,
        padding: 16,
        marginHorizontal: 8,
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: {
            width: 0,
            height: 2,
        },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 2,
    },
    recipeImagePlaceholder: {
        width: 60,
        height: 60,
        backgroundColor: colors.surfaceLight,
        borderRadius: 30,
        marginBottom: 12,
    },
    recipeName: {
        fontSize: 14,
        fontWeight: '600',
        color: colors.text,
        textAlign: 'center',
    },
    calorieTracker: {
        backgroundColor: colors.cardBackground,
        borderRadius: 12,
        padding: 24,
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: {
            width: 0,
            height: 2,
        },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 2,
    },
    calorieTrackerText: {
        fontSize: 16,
        fontWeight: '600',
        color: colors.text,
    },
    bottomNav: {
        marginBottom: 32,
    },
    navButton: {
        height: 48,
        borderRadius: 12,
        marginBottom: 12,
    },
    navButtonInner: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    navButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: colors.textInverse,
    },
});

export default HomeScreen;