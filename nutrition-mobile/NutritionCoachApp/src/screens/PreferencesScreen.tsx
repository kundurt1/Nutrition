import React, { useState } from 'react';
import {
    View,
    Text,
    ScrollView,
    TextInput,
    TouchableOpacity,
    SafeAreaView,
    StyleSheet,
    Switch,
    Alert,
} from 'react-native';
import { useAuth } from '../contexts/AuthContext';
import { colors } from '../styles/colors';

const PreferencesScreen = () => {
    const { signOut } = useAuth();
    const [budget, setBudget] = useState('20-30');
    const [allergies, setAllergies] = useState('Shellfish, Eggs, Soy');
    const [diet, setDiet] = useState('Flexible');
    const [followingDiet, setFollowingDiet] = useState(false);
    const [saving, setSaving] = useState(false);

    const dietOptions = [
        'Flexible',
        'Vegetarian',
        'Vegan',
        'Keto',
        'Paleo',
        'Mediterranean',
        'Low Carb'
    ];

    const handleSave = async () => {
        setSaving(true);

        // Simulate save operation
        setTimeout(() => {
            setSaving(false);
            Alert.alert('Success', 'Preferences saved successfully!');
        }, 1500);
    };

    const handleSignOut = async () => {
        Alert.alert(
            'Sign Out',
            'Are you sure you want to sign out?',
            [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Sign Out', style: 'destructive', onPress: signOut }
            ]
        );
    };

    const DietSelector = () => (
        <View style={styles.dietSelector}>
            {dietOptions.map((option) => (
                <TouchableOpacity
                    key={option}
                    style={[
                        styles.dietOption,
                        diet === option && styles.dietOptionActive
                    ]}
                    onPress={() => setDiet(option)}
                >
                    <Text style={[
                        styles.dietOptionText,
                        diet === option && styles.dietOptionTextActive
                    ]}>
                        {option}
                    </Text>
                </TouchableOpacity>
            ))}
        </View>
    );

    return (
        <SafeAreaView style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <Text style={styles.headerTitle}>Set your preferences</Text>
                <Text style={styles.headerSubtitle}>
                    What is your budget range and do you have any allergies or foods you want to avoid?
                </Text>
            </View>

            <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
                <View style={styles.formContainer}>
                    {/* Budget Section */}
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Budget Range</Text>
                        <TextInput
                            style={styles.textInput}
                            value={budget}
                            onChangeText={setBudget}
                            placeholder="$0-100"
                        />
                    </View>

                    {/* Allergies Section */}
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>
                            Enter any allergies or foods you want to avoid
                        </Text>
                        <TextInput
                            style={[styles.textInput, styles.textArea]}
                            value={allergies}
                            onChangeText={setAllergies}
                            placeholder="Shellfish, Eggs, Soy"
                            multiline
                            numberOfLines={3}
                        />
                    </View>

                    {/* Diet Question */}
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>
                            Is there a particular diet you want to follow?
                        </Text>
                        <View style={styles.switchContainer}>
                            <Text style={styles.switchLabel}>Following a specific diet</Text>
                            <Switch
                                value={followingDiet}
                                onValueChange={setFollowingDiet}
                                trackColor={{ false: colors.border, true: colors.primary }}
                                thumbColor={followingDiet ? colors.cardBackground : colors.textLight}
                            />
                        </View>
                    </View>

                    {/* Diet Selector */}
                    {followingDiet && (
                        <View style={styles.section}>
                            <Text style={styles.sectionTitle}>Select your diet</Text>
                            <DietSelector />
                        </View>
                    )}

                    {/* Menu Items Section */}
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Menu Item</Text>
                        <View style={styles.menuItems}>
                            {['Menu Item', 'Menu Item', 'Menu Item', 'Menu Item'].map((item, index) => (
                                <TouchableOpacity key={index} style={styles.menuItem}>
                                    <Text style={styles.menuItemText}>{item}</Text>
                                </TouchableOpacity>
                            ))}
                        </View>
                    </View>

                    {/* Save Button */}
                    <TouchableOpacity
                        style={[styles.saveButton, saving && styles.saveButtonDisabled]}
                        onPress={handleSave}
                        disabled={saving}
                    >
                        <Text style={styles.saveButtonText}>
                            {saving ? 'Saving...' : 'Save Preferences'}
                        </Text>
                    </TouchableOpacity>

                    {/* Sign Out Button */}
                    <TouchableOpacity
                        style={styles.signOutButton}
                        onPress={handleSignOut}
                    >
                        <Text style={styles.signOutButtonText}>Sign Out</Text>
                    </TouchableOpacity>
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
        paddingTop: 20,
        paddingBottom: 24,
        paddingHorizontal: 16,
        alignItems: 'center',
    },
    headerTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: colors.text,
        marginBottom: 8,
        textAlign: 'center',
    },
    headerSubtitle: {
        fontSize: 14,
        color: colors.textSecondary,
        textAlign: 'center',
        lineHeight: 20,
    },
    scrollView: {
        flex: 1,
        paddingHorizontal: 16,
    },
    formContainer: {
        backgroundColor: colors.cardBackground,
        borderRadius: 16,
        padding: 20,
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
    section: {
        marginBottom: 24,
    },
    sectionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: colors.text,
        marginBottom: 12,
    },
    textInput: {
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: 8,
        padding: 12,
        fontSize: 16,
        color: colors.text,
        backgroundColor: colors.background,
    },
    textArea: {
        minHeight: 80,
        textAlignVertical: 'top',
    },
    switchContainer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 8,
    },
    switchLabel: {
        fontSize: 16,
        color: colors.text,
    },
    dietSelector: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 8,
    },
    dietOption: {
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: colors.border,
        backgroundColor: colors.background,
    },
    dietOptionActive: {
        backgroundColor: colors.primary,
        borderColor: colors.primary,
    },
    dietOptionText: {
        fontSize: 14,
        color: colors.text,
        fontWeight: '500',
    },
    dietOptionTextActive: {
        color: colors.textInverse,
    },
    menuItems: {
        gap: 12,
    },
    menuItem: {
        backgroundColor: colors.background,
        borderRadius: 8,
        padding: 16,
        borderWidth: 1,
        borderColor: colors.border,
    },
    menuItemText: {
        fontSize: 16,
        color: colors.text,
    },
    saveButton: {
        backgroundColor: colors.primary,
        borderRadius: 12,
        paddingVertical: 16,
        alignItems: 'center',
        marginTop: 8,
        marginBottom: 16,
    },
    saveButtonDisabled: {
        opacity: 0.6,
    },
    saveButtonText: {
        color: colors.textInverse,
        fontSize: 16,
        fontWeight: '600',
    },
    signOutButton: {
        backgroundColor: colors.error,
        borderRadius: 12,
        paddingVertical: 16,
        alignItems: 'center',
    },
    signOutButtonText: {
        color: colors.textInverse,
        fontSize: 16,
        fontWeight: '600',
    },
});

export default PreferencesScreen;